import logging
import numpy as np
import Levenshtein
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import DashboardData, ImageModel, OcrResult, State, StateBase, StateUpdate, User, BoatPass, BoatPassCreate, BoatPassPublic, BoundingBox, OcrResultPublic, PaymentStatusEnum, BoatLengthEnum, StateOfBoatEnum, ImagePayload, WebsocketImageData
from app import crud

"""
StateController
In this file there are functions to manage the State in the database.
Firstly the assigments of boat_passes to state needs to be proceed. 
After that the business logic handle casess of pass throughs or harbour management.

StateAssigment
At least 3 boat_passes in the time span of X seconds needed to create a new state
IdentificationCase1 - full identification by full match of detected_identifier
IdentificationCase2 - following the bounding box flow in the frames
IdentificationCase3 - partial match of detected_identifier, measure editing distance between identifiers
Catch the case when there is multiple boat passes forming one state, but some boat_state is not identified in the right way.
Initially when there are 3 boat_passes create a new state if needed, for next boat_pass and right identification expand the state with new boat_pass.

StateBusinessLogic
Boat pass through - pass_in pass_out events raised by cameras in the timespan of 1 minute
Boat parked - only the pass_in event is known, or the time difference is greater than 15 minutes
"""

logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

def manage_boat_pass_state_assignment(boat_pass_res: BoatPass, session: Session) -> BoatPass:
    history_range = timedelta(seconds=app_config.BOAT_PASS_TIMEDELTA_SECONDS)
    recent_boat_passes = crud.get_recent_boat_passes(session=session, timestamp=boat_pass_res.timestamp, timedelta=history_range)
    if len(recent_boat_passes) < 2:
        logger.debug(f"Less than 2 recent boat passes in the time span of {history_range} seconds")
        return boat_pass_res
    else:
        logger.debug(f"Found {len(recent_boat_passes)} boat passes in the time span of {history_range} seconds")        
        if check_boat_passes_identification([boat_pass_res] + recent_boat_passes):
            state = recent_boat_passes[0].state
            if state is None:
                state = StateBase(arrival_time=boat_pass_res.timestamp, 
                        departure_time=None, 
                        best_detected_identifier=boat_pass_res.detected_identifier, 
                        best_detected_boat_length=boat_pass_res.boat_length, 
                        payment_status=PaymentStatusEnum.nezaplaceno, 
                        time_in_marina=0, 
                        state_of_boat=StateOfBoatEnum.kotvi)
                state = crud.create_state(session=session, state=state)

                for recent_boat_pass in recent_boat_passes:
                    recent_boat_pass.state = state
                    recent_boat_pass.state_id = state.id
                    crud.update_instance(session=session, instance=recent_boat_pass)
                    logger.debug(f"Assigned state {state.id} to boat pass: {recent_boat_pass}")
            
            boat_pass_res.state = state
            boat_pass_res.state_id = state.id
            crud.update_instance(session=session, instance=boat_pass_res)
            update_best_detected_identifier_by_majority(state, session)
            logger.debug(f"Assigned state {state.id} to boat pass: {boat_pass_res}")
        else:
            # TODO: handle the case when the boat passes are not identified correctly
            # that about the case when 4 of 5 boat passes are identified correctly ??
            logger.error(f"Boat passes are not identified correctly {boat_pass_res}")
            pass
            
        manage_business_logic_for_state(state, session)
        return boat_pass_res

def update_best_detected_identifier_by_majority(state: State, session: Session) -> State:
    """
    Update the best_detected_identifier for the state by majority voting given by the boat passes
    """
    boat_passes = state.boat_passes
    detected_identifiers = [boat_pass.detected_identifier for boat_pass in boat_passes if boat_pass.detected_identifier is not None]
    if len(detected_identifiers) == 0:
        return state
    else:
        best_detected_identifier = max(set(detected_identifiers), key=detected_identifiers.count)
        state.best_detected_identifier = best_detected_identifier
        crud.update_instance(session=session, instance=state)
        return state    

def check_boat_passes_identification(boat_passes: list[BoatPass]) -> bool:
    if check_matching_detected_identifier(boat_passes):
        logger.debug("Boat passes have matching detected identifier")
        return True
        
    elif check_matching_bounding_boxes(boat_passes):
        logger.debug("Boat passes have matching bounding boxes")
        return True

    elif check_partial_matching_detected_identifier(boat_passes):
        logger.debug("Boat passes have partial matching detected identifier")
        return True

    logger.debug("Boat passes have no matching identification")
    return False

def check_matching_detected_identifier(boat_passes: list[BoatPass]) -> bool:
    detected_identifier = boat_passes[0].detected_identifier
    if all(boat_pass.detected_identifier == detected_identifier for boat_pass in boat_passes):
        return True
    return False

def check_matching_bounding_boxes(boat_passes: list[BoatPass]) -> bool:
    center_of_boxes = []
    for boat_pass in boat_passes:
        filtered_boxes = [box for box in boat_pass.bounding_boxes if box.confidence >= 0.5]
        if len(filtered_boxes) == 0:
            return False
        center_of_mass = calculate_center_of_mass(filtered_boxes)
        if center_of_mass[0] is not None:
            center_of_boxes.append(center_of_mass)
        else:
            return False
    
    # monitor the distance between the centers of the bounding boxes, if the difference in x axis movements has small variance, the bounding boxes are matching
    x_shifts = [center_of_boxes[i + 1][0] - center_of_boxes[i][0] for i in range(len(center_of_boxes) - 1)]
    if  len(x_shifts) >= 2 and np.std(x_shifts) < 0.2 * np.abs(np.mean(x_shifts)):
        return True
    else:
        return False

            
def check_partial_matching_detected_identifier(boat_passes: list[BoatPass]) -> bool:
    # calculate the levenshtein distance between the detected identifiers, if any of pairwise distances is greater then 1 then no match
    max_levenstein_distance = 0
    for i in range(len(boat_passes) - 1):
        for j in range(i + 1, len(boat_passes)):
            levenstein_distance = Levenshtein.distance(boat_passes[i].detected_identifier, boat_passes[j].detected_identifier)
            if levenstein_distance > max_levenstein_distance:
                max_levenstein_distance = levenstein_distance
    return max_levenstein_distance <= 1


def manage_business_logic_for_state(state: State, session: Session) -> State:
    """
    Load BoatPasses for the state
    Split boatpasses by cameras, or time continuity
    Calculate/create/handle the pass_in and pass_out events
    """
    # boat_passes = crud.get_boat_passes_by_state_id(session=session, state_id=state.id)
    boat_passes = state.boat_passes
    boat_passes = sorted(boat_passes, key=lambda x: x.timestamp)

    # split boat passes by cameras and time continuity
    split_boat_passes = [[]]
    current_camera_id = boat_passes[0].camera_id
    current_timestamp = boat_passes[0].timestamp
    for boat_pass in boat_passes:
        if boat_pass.camera_id != current_camera_id or boat_pass.timestamp - current_timestamp > timedelta(seconds=app_config.BOAT_PASS_TIMEDELTA_SECONDS):
            split_boat_passes.append([])
            current_camera_id = boat_pass.camera_id
            current_timestamp = boat_pass.timestamp
        split_boat_passes[-1].append(boat_pass)
        
    # handle continous boat passes, decide pass_in pass_out events
    pass_in = False
    pass_out = False
    for boat_passes in split_boat_passes:
        dominant_x_movement = calculate_dominant_x_movement(boat_passes)
        if boat_passes[0].camera_id == 1:
            if dominant_x_movement == 1:
                pass_in = True
            elif dominant_x_movement == -1:
                pass_out = True
        elif boat_passes[0].camera_id == 2:
            if dominant_x_movement == 1:
                pass_out = True
            elif dominant_x_movement == -1:
                pass_in = True
    
    # TODO: validate this logic
    logger.debug(f"DEBUGGING INFO pass_in {pass_in}, pass_out {pass_out} for the satate {state}.")

    if pass_in and pass_out:
        # the boat has pass thorugh or exited the harbour
        if state.state_of_boat == StateOfBoatEnum.kotvi:
            state.state_of_boat = StateOfBoatEnum.prujezd
        state.departure_time = split_boat_passes[-1][-1].timestamp
        time_differece = split_boat_passes[-1][-1].timestamp - split_boat_passes[0][0].timestamp
        # TODO: discuss if there should be state Prujezd and Odjezd
        if time_differece > timedelta(minutes=15):
            state.time_in_marina = time_differece.total_seconds() / 60
        crud.update_instance(session=session, instance=state)
        logger.debug(f"State updated {state}.")
    elif pass_in and not pass_out:
        # the boat has entered the harbour
        logger.debug(f"The boat has entered the harbour {state}.")
    elif not pass_in and pass_out:
        # the boat is exiting the harbour, probably the boat was parked or was added manually
        # find adequate/matching state "kotvi" in database
        states_in_harbour = crud.get_states_in_harbour(session=session)
        state.departure_time = split_boat_passes[-1][-1].timestamp
        crud.update_instance(session=session, instance=state)
        logger.debug(f"State updated {state}.")
        states_merged = False
        for state_in_harbour in states_in_harbour:            
            if state.best_detected_identifier == state_in_harbour.best_detected_identifier:
            ## TODO: possibility to add a partial identifiers match
            # if state.best_detected_identifier == state_in_harbour.best_detected_identifier \
            #     or Levenshtein.distance(state.best_detected_identifier, state_in_harbour.best_detected_identifier) < 2:
                state = merge_states(state, state_in_harbour, session)
                states_merged = True
                logger.debug(f"State merged and updated {state}.")
                break
        if not states_merged:
            # the boat has not been detected when entering
            logger.error(f"The boat is exiting the harbour, but has not been detected when entering {state}.")
    else:
        # strange state, catch it
        logger.error(f"Strange state, catch it {state}.")


def merge_states(state_departure: State, state_in_harbour: State, session: Session) -> State:
    state_in_harbour.departure_time = state_departure.departure_time
    state_in_harbour.state_of_boat = StateOfBoatEnum.prujezd
    state_in_harbour.time_in_marina = (state_in_harbour.departure_time - state_in_harbour.arrival_time).total_seconds() / 60
    for boat_pass in state_departure.boat_passes:
        boat_pass.state = state_in_harbour
        boat_pass.state_id = state_in_harbour.id
        crud.update_instance(session=session, instance=boat_pass)
    crud.delete_instance(session=session, instance=state_departure)
    crud.update_instance(session=session, instance=state_in_harbour)
    return state_in_harbour

def calculate_dominant_x_movement(boat_passes: list[BoatPass]) -> float:
    """
    Calculate the dominant movement gradient of the boat passes
    """
    sorted_newest_to_oldest_passes = sorted(boat_passes, key=lambda x: x.timestamp)
    x_movements = []
    for i in range(len(sorted_newest_to_oldest_passes) - 1):
        current_pass = sorted_newest_to_oldest_passes[i]
        next_pass = sorted_newest_to_oldest_passes[i + 1]
        current_com = calculate_center_of_mass(current_pass.bounding_boxes)
        next_com = calculate_center_of_mass(next_pass.bounding_boxes)
        x_movements.append(next_com[0] - current_com[0])
    
    negative_movements_count = len([x for x in x_movements if x < 0])
    positive_movements_count = len([x for x in x_movements if x > 0])
    if negative_movements_count > positive_movements_count:
        return -1
    elif negative_movements_count < positive_movements_count:
        return 1
    else:
        return 0

def calculate_first_last_x_axis_movement(boat_passes: list[BoatPass]) -> float:
    """
    Calculate the movement gradient between the first and last boat pass
    """
    sorted_newest_to_oldest_passes = sorted(boat_passes, key=lambda x: x.timestamp)
    newest_com = calculate_center_of_mass(sorted_newest_to_oldest_passes[0].bounding_boxes)
    oldest_com = calculate_center_of_mass(sorted_newest_to_oldest_passes[-1].bounding_boxes)
    return newest_com[0] - oldest_com[0]

def calculate_center_of_mass(bounding_boxes: list[BoundingBox]) -> tuple[float, float]:
    """
    Calculate the center of mass for the boat pass
    """
    if len(bounding_boxes) == 1:
        return ((bounding_boxes[0].left + bounding_boxes[0].right) / 2, (bounding_boxes[0].top + bounding_boxes[0].bottom) / 2)
    elif len(bounding_boxes) > 1:
        # in case of multiple bounding boxes, try to merge them into one box
        sorted_boxes = sorted(bounding_boxes, key=lambda x: x.left)
        # check adjecent boxes, there should be overlap or maximal Xpx gap
        boxes_for_merge_flag = True
        for i in range(len(sorted_boxes) - 1):
            if sorted_boxes[i].right + app_config.MAX_GAP_BETWEEN_CONTINOUES_BOUNDING_BOXES < sorted_boxes[i + 1].left:
                boxes_for_merge_flag = False
                break
        if boxes_for_merge_flag:
            return sorted_boxes[0].left + sorted_boxes[-1].right / 2, sorted_boxes[0].top + sorted_boxes[-1].bottom / 2
    return None, None