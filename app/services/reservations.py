from datetime import date, datetime, time, timedelta

MAX_RESERVATION_DURATION = timedelta(hours=4)


class ReservationDurationExceeded(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "La reserva no puede superar cuatro horas consecutivas."
        )


def validate_reservation_duration(start_time: time, end_time: time) -> None:
    start = datetime.combine(date.min, start_time)
    end = datetime.combine(date.min, end_time)
    if end - start > MAX_RESERVATION_DURATION:
        raise ReservationDurationExceeded
