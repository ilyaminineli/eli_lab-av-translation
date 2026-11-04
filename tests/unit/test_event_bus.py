from core.event_bus import EventBus


def test_event_bus_delivers_payload_and_unsubscribes() -> None:
    bus = EventBus()
    received = []

    def handler(**payload):
        received.append(payload)

    bus.subscribe("media.loaded", handler)
    bus.publish("media.loaded", deck_id="deck_a")
    bus.unsubscribe("media.loaded", handler)
    bus.publish("media.loaded", deck_id="deck_b")
    assert received == [{"deck_id": "deck_a"}]
