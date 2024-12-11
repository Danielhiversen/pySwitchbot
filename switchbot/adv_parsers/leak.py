def process_leak(data: bytes | None, mfr_data: bytes | None) -> dict[str, bool | int]:
    """Process SwitchBot Water Leak Detector advertisement data."""
    if data is None and mfr_data is None:
        return {}

    water_leak_detected = None
    device_tampered = None
    battery_level = None
    low_battery = None

    if data and len(data) >= 3:
        # Byte 0: Model ID
        model_id = data[0]
        if model_id != 0x26:
            # Not a Water Leak Detector
            return {}
        # Byte 1: Event Flags
        event_flags = data[1]
        water_leak_detected = bool(event_flags & 0b00000001)  # Bit 0
        device_tampered = bool(event_flags & 0b00000010)  # Bit 1
        # Byte 2: Battery Info
        battery_info = data[2]
        battery_level = battery_info & 0b01111111  # Bits 0-6
        low_battery = bool(battery_info & 0b10000000)  # Bit 7

    # Manufacturer data can be processed here if needed

    return {
        "water_leak_detected": water_leak_detected,
        "device_tampered": device_tampered,
        "battery_level": battery_level,
        "low_battery": low_battery,
    }
