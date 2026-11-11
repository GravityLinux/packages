# SPDX-License-Identifier: MIT
from pathlib import Path
from tempfile import TemporaryDirectory
from first_run import seed_text, seed_file

tool='proton-gravity-arm64'
old_tool='proton-gravity-arm64-research'
blank,changed=seed_text('',tool,75)
assert changed and '"priority" "75"' in blank
assert seed_text(blank,'another',250)==(blank,False)
# Add only missing settings blocks; preserve unrelated values and comments.
old='// comment\n"InstallConfigStore" { "Unrelated" "a\\\\b" }\n'
new,changed=seed_text(old,tool,75)
assert changed and '// comment' in new and '"Unrelated" "a\\\\b"' in new
# Preserve an existing user/global choice, including an explicitly empty name.
existing='"InstallConfigStore" { "Software" { "Valve" { "Steam" { "CompatToolMapping" { "0" {"name" ""} "12" {"name" "custom"} } } } } }'
assert seed_text(existing,tool,75)==(existing,False)
# Reject malformed settings rather than overwriting them.
for bad in ['"InstallConfigStore" {', '"InstallConfigStore" "scalar"', '}']:
    try: seed_text(bad,tool,75)
    except ValueError: pass
    else: raise AssertionError(bad)
# Follow a rename: mappings naming the old tool (global and per game) move to
# the new name; other tools and the priority stay; idempotent afterwards.
renamed='"InstallConfigStore" { "Software" { "Valve" { "Steam" { "CompatToolMapping" { "0" { "name" "proton-gravity-arm64-research" "config" "" "priority" "75" } "12" {"name" "proton-gravity-arm64-research"} "13" {"name" "custom"} } } } } }'
new,changed=seed_text(renamed,tool,75,(old_tool,))
assert changed and old_tool not in new and new.count('"proton-gravity-arm64"')==2 and '"custom"' in new and '"priority" "75"' in new
assert seed_text(new,tool,75,(old_tool,))==(new,False)
# A name outside CompatToolMapping is left alone.
other='"InstallConfigStore" { "Other" { "name" "proton-gravity-arm64-research" } }'
new,changed=seed_text(other,tool,75,(old_tool,))
assert changed and new.startswith(other[:-2])
with TemporaryDirectory() as d:
    p=Path(d)/'config/config.vdf'
    assert seed_file(p,tool,75)
    before=p.read_bytes();stat=p.stat()
    assert not seed_file(p,tool,75) and p.read_bytes()==before and p.stat().st_mtime_ns==stat.st_mtime_ns
    link=Path(d)/'link';link.symlink_to(p)
    try:seed_file(link,tool,75)
    except ValueError:pass
    else:raise AssertionError('symlink accepted')
print('PASS: first-run policy follows renames, preserves choices/bytes, handles absence, rejects malformed/symlinked config, idempotent')
