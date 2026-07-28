from mood_tracker.presentation.handlers import fields_router


def test_fields_router_includes_all_management_flows() -> None:
    assert {router.name for router in fields_router.sub_routers} == {
        "fields_display",
        "fields_form",
        "fields_ordering",
        "fields_overview",
    }
