from datetime import datetime


def isoformat_timestamp(timestamp: datetime) -> str:
    return datetime.fromtimestamp(int(timestamp.timestamp() * 1000) / 1000.0).isoformat()
