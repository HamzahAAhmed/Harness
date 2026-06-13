from journey.harness.alarms import create_alarm


def test_alarm_has_required_structured_fields():
    alarm = create_alarm(run_id="run", alarm_type="GROUNDING_VIOLATION", severity="error", stage="grounding", context={"unknown": "x"}, recommended_action="Use a supplied place ID.")
    assert alarm.alarm_type == "GROUNDING_VIOLATION"
    assert alarm.severity == "error"
    assert alarm.context
    assert alarm.recommended_action
