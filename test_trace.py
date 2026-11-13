from ethscan.trace import format_trace_report_markdown, format_trace_report_csv, format_trace_report_json

# Test with hostile hops
hostile_shapes = [None, 1, True, 1.5, 'string', b'bytes', [], [1, 2, 3], {'a': 1}, (1, 2), [None, 1, 'two', 3.0], [{'a': 1}, {'b': 2}]

print('=== Testing format_trace_report_* with hostile hops ===')
for shape in hostile_shapes:
    data = {
        'target': 'example.com',
        'host': 'example.com',
        'ip': '93.184.216.34',
        'dst_ip': '93.184.216.34',
        'port': 80,
        'max_hops': 30,
        'timeout': 2.0,
        'probes_per_hop': 3,
        'raw_socket_available': False,
        'hops': shape,
        'hop_count': 0,
        'destination_reached': False,
        'reached_destination': False,
        'reached': False,
        'notes': [],
        'recursive': False,
    }
    for name, fn in [('MD', format_trace_report_markdown), ('CSV', format_trace_report_csv), ('JSON', format_trace_report_json)]:
        try:
            out = fn(data)
            print(f'{name} OK for {type(shape).__name__}: {shape!r}')
        except Exception as e:
            print(f'{name} CRASH for {type(shape).__name__}: {shape!r} -> {type(e).__name__}: {e}')