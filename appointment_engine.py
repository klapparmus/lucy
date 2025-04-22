from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel

# Simulated dependencies
import db  # Assume a database interface
import mls_api  # Simulated MLS API
from calendar_api import is_slot_available, create_calendar_event
from route_optimizer import update_route_plan
from messaging import send_sms

class Appointment(BaseModel):
    listing_id: str
    property_address: str
    seller: dict
    listing_agent: dict
    assistant: dict
    requested_by: str
    datetime: datetime
    status: Literal["pending", "confirmed", "cancelled"]
    constraints: list[str]
    confirmations: dict[str, bool]
    calendar_event_id: Optional[str] = None

def parse_constraints(notes: str):
    # Dummy constraint parser
    constraints = []
    if "24h notice" in notes.lower():
        constraints.append("24h notice")
    if "no weekends" in notes.lower():
        constraints.append("no weekends")
    return constraints

def create_appointment(request):
    listing_id = request["listing_id"]
    datetime_requested = request["datetime"]

    listing = mls_api.get_listing(listing_id)
    constraints = parse_constraints(listing.get("notes", ""))

    if not is_slot_available(request["agent_email"], datetime_requested):
        return {"error": "Slot unavailable. Suggest alternative."}

    appointment = Appointment(
        listing_id=listing_id,
        property_address=listing["address"],
        seller=listing["seller"],
        listing_agent=listing["agent"],
        assistant=listing["assistant"],
        requested_by=request["agent_email"],
        datetime=datetime_requested,
        status="pending",
        constraints=constraints,
        confirmations={"seller": False, "agent": False, "assistant": False}
    )

    db.save(appointment)
    dispatch_confirmations(appointment)

    return {"status": "pending", "appointment_id": appointment.listing_id}

def dispatch_confirmations(appointment: Appointment):
    for role, person in [("seller", appointment.seller),
                         ("agent", appointment.listing_agent),
                         ("assistant", appointment.assistant)]:
        send_sms(
            to=person["contact"],
            message=f"Please confirm showing for {appointment.property_address} on {appointment.datetime}"
        )

def confirm_participant(appointment_id: str, role: str):
    appointment = db.get(appointment_id)
    appointment.confirmations[role] = True

    if all(appointment.confirmations.values()):
        appointment.status = "confirmed"
        appointment.calendar_event_id = create_calendar_event(appointment)
        update_route_plan(appointment.requested_by)

    db.update(appointment)
    return appointment.status

def reschedule_appointment(appointment_id: str, new_time: datetime):
    appointment = db.get(appointment_id)
    appointment.datetime = new_time
    appointment.status = "pending"
    appointment.confirmations = {k: False for k in appointment.confirmations}
    dispatch_confirmations(appointment)
    db.update(appointment)
