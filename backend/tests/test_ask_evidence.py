from odin.services.ask_evidence import records_for, incident_calculations, deadline_calculations, sla_calculations, invalid_comparison, calculation_claims, select_records, incorrect_deadline, AskCitation, coverage_claims
import json


def test_official_event_body_is_decoded_before_quote_verification():
    raw = json.dumps({'body': 'Duration: 90 minutes\nNo Scheduled Maintenance.'})
    record = records_for({'events_so_far': [{'id': 'one', 'raw': raw}]}, ['A'])[0]
    assert 'minutes\nNo Scheduled' in record['text'] and '\\n' not in record['text']


def test_record_scope_and_held_inputs_are_excluded():
    context = {'events_so_far': [
        {'id': 'ok', 'raw': 'Allowed fact', 'contract_ids': ['A']},
        {'id': 'foreign', 'raw': 'Outside selection', 'contract_ids': ['B']},
        {'id': 'held', 'status': 'quarantined', 'raw': 'Private held input'},
        {'id': 'bad', 'status': 'rejected', 'raw': 'Rejected input'}],
        'ledger': [{'contract_id': 'B', 'reference': 'Other contract'}]}
    assert [r['source_id'] for r in records_for(context, ['A'])] == ['ok']


def test_uptime_merges_duplicates_and_splits_months():
    def event(identity, start, end):
        return {'source_id': identity, 'source_type': 'event', 'text':
                f'Complete unavailability. Incident start: {start}\nIncident end: {end}'}
    records = [event('one', '2028-02-29 23:00', '2028-03-01 01:00'),
               event('duplicate', '2028-02-29 23:30', '2028-03-01 00:30')]
    results = incident_calculations(records)
    assert [r['observed_downtime_minutes'] for r in results] == [60, 60]
    assert results[0]['calendar_minutes'] == 29 * 1440
    assert results[1]['calendar_minutes'] == 31 * 1440


def test_partial_degradation_does_not_become_total_unavailability():
    assert incident_calculations([{'source_id': 'one', 'source_type': 'event', 'text':
        '60% requests failed. Incident start: 2027-05-01 01:00\nIncident end: 2027-05-01 02:00'}]) == []


def test_request_deadline_uses_calendar_arithmetic_not_model_day_counts():
    passages = [{'contract_id': 'sample', 'clause_number': '3', 'text':
                 'Request within forty-five (45) days after the end of the calendar month.'}]
    records = [{'source_id': 'request', 'source_type': 'event', 'title': 'Credit Request', 'date': '2027-06-15T10:30:00Z'}]
    calculated = deadline_calculations(passages, records, [{'month': '2027-03'}])[0]
    assert calculated['deadline'] == '2027-05-15'
    assert calculated['request_records'][0]['days_after_month_end'] == 76
    assert calculated['request_records'][0]['days_after_deadline'] == 31


def test_threshold_comparison_and_nominal_credit_are_computed():
    passages = [{'contract_id': 'sample', 'clause_number': '1', 'heading': 'Uptime Commitment', 'text': 'Uptime at least 99.9%.'},
                {'contract_id': 'sample', 'clause_number': 'cap', 'text': 'Service credits will not exceed twenty percent (20%) of the Monthly Fee.'},
                {'contract_id': 'sample', 'clause_number': '2', 'text': 'Monthly Fee: $40,000.00'},
                {'contract_id': 'sample', 'clause_number': '3', 'text': 'Credit fifteen percent (15%) of the Monthly Fee.'}]
    result = sla_calculations(passages, [{'month': '2027-03', 'uptime_if_no_other_countable_downtime': 99.574373}])[0]
    assert not result['target_met'] and result['nominal_credit'] == 6000
    passages[1]['text'] = 'Service credits will not exceed ten percent (10%) of the Monthly Fee.'
    capped = sla_calculations(passages, [{'month': '2027-03', 'uptime_if_no_other_countable_downtime': 99.574373}])[0]
    assert capped['nominal_credit'] == 4000 and capped['credit_cap_percent'] == 10
    assert invalid_comparison('99.574% exceeded the target of 99.9%.')
    assert not invalid_comparison('99.574% is below the target of 99.9%.')


def test_computed_summary_keeps_financial_evidence_when_prose_omits_it():
    passages = [{'contract_id': 'sample', 'clause_number': '1', 'heading': 'Uptime Commitment', 'text': 'Availability is ninety percent (90%).'},
                {'contract_id': 'sample', 'clause_number': '2', 'text': 'Monthly Fee: $2,000.00'},
                {'contract_id': 'sample', 'clause_number': '3', 'text': 'Credit ten percent (10%) of the Monthly Fee.'}]
    records = [{'source_id': 'incident', 'source_type': 'event', 'text':
                'Complete unavailability. Incident start: 2028-02-01 00:00\nIncident end: 2028-02-05 00:00\nDuration: 5760 minutes'}]
    incidents = incident_calculations(records)
    context = {'incident_calculations': incidents, 'sla_calculations': sla_calculations(passages, incidents)}
    claims = calculation_claims('What was uptime and what do we owe?', context, passages, records)
    assert '$200.00' in claims[0]['text'] and 'eligibility unverified' in claims[0]['text']
    assert {c['source_type'] for c in claims[0]['citations']} == {'contract', 'event'}
    for citation in claims[0]['citations']:
        source = records[0]['text'] if citation['source_type'] == 'event' else next(p['text'] for p in passages if p['clause_number'] == citation['clause_number'])
        assert citation['quote'] in source


def test_record_selection_preserves_explicit_ids_among_irrelevant_entries():
    records = [{'source_id': str(i), 'source_type': 'ledger', 'text': 'Ordinary payment', 'title': 'Invoice'} for i in range(30)]
    records += [{'source_id': 'incident-xyz', 'source_type': 'event', 'text': 'Rare evidence', 'title': 'Incident'}]
    assert any(r['source_id'] == 'incident-xyz' for r in select_records('Explain incident-xyz', records))


def test_incorrect_model_deadline_is_rejected_despite_authentic_contract_quote():
    context = {'deadline_calculations': [{'contract_id': 'sample', 'request_window_days': 45,
        'deadline': '2027-05-15', 'month_end': '2027-03-31', 'request_records': [{'record_date': '2027-06-15'}]}]}
    citations = [AskCitation(contract_id='sample', clause_number='1', quote='within 45 days')]
    assert incorrect_deadline('The 45 days after March 31, 2027 deadline was April 30, 2027.', citations, context)
    assert not incorrect_deadline('The deadline was May 15, 2027, 45 days after March 31, 2027.', citations, context)


def test_expiry_summary_is_conditional_and_has_both_rule_and_record_sources():
    passages = [{'contract_id': 'sample', 'clause_number': '9', 'text': 'A lapse in required insurance coverage constitutes a material breach of this Agreement.'}]
    records = [{'source_id': 'context', 'source_type': 'company', 'text': 'Expiry: June 30, 2028'}]
    claim = coverage_claims('Is the company in breach?', passages, records)[0]
    assert 'If required coverage lapsed' in claim['text'] and 'June 30, 2028' in claim['text']
    assert {c['source_type'] for c in claim['citations']} == {'company', 'contract'}
