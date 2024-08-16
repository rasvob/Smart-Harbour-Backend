import logging
from sqlmodel import Session, select
from app.core.app_logger import AppLogger
from app.core.app_config import app_config
from app.models import DashboardData, ImageModel, OcrResult, State, StateBase, StateUpdate, User, BoatPass, BoatPassCreate, BoatPassPublic, OcrResultPublic, PaymentStatusEnum, BoatLengthEnum, StateOfBoatEnum, ImagePayload, WebsocketImageData
from app import crud


logger = AppLogger(__name__, logging._nameToLevel[app_config.LOG_LEVEL]).get_logger()

def manage_state_for_boat_pass(boat_pass_res: BoatPass, session: Session) -> BoatPass:
        

    """
    select the n last boat passes and check if the boat is the same
    in case of the same boat, update the state
    otherwise create a new state
    """
    history_length = 10
    boat_passes = crud.get_last_n_boat_passes_for_timestamp(session=session, timestamp=boat_pass_res.timestamp, n=history_length)
    state_found = False
    for previous_boat_pass in boat_passes:
        if previous_boat_pass.detected_identifier == boat_pass_res.detected_identifier:
            state_found = True
            previous_paired_state = previous_boat_pass.state
            # TODO: update departure time?
            
            boat_pass_res.state = previous_paired_state
            boat_pass_res.state_id = previous_paired_state.id

            print('boat_pass_res', boat_pass_res)
            crud.update_instance(session=session, instance=boat_pass_res)

            # list all boat passes in the state for debugging purposes
            state = session.query(State).filter(State.id == previous_paired_state.id).one()
            print(state)
            for boat_pass in state.boat_passes:
                logger.debug(f"Boat pass in state: {boat_pass}")

            break
    if not state_found:
        state = StateBase(arrival_time=boat_pass_res.timestamp, 
                        departure_time=boat_pass_res.timestamp, 
                        best_detected_identifier=boat_pass_res.detected_identifier, 
                        best_detected_boat_length=boat_pass_res.boat_length, 
                        payment_status=PaymentStatusEnum.nezaplaceno, 
                        time_in_marina=0, 
                        state_of_boat=StateOfBoatEnum.prujezd)
        state_rec = crud.create_state(session=session, state=state)

        print('state_rec', state_rec)
        boat_pass_res.state = state_rec
        crud.update_instance(session=session, instance=boat_pass_res)

        print('boat_pass_res', boat_pass_res)
        logger.debug(f"Created state: {state_rec}")

    return boat_pass_res