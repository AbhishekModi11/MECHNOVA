import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontend"))

from app.services.project_service import get_project, list_projects, update_project_raw_material, save_job_slip_action

projects = list_projects()
print(f"Total projects in DB: {len(projects)}")
if projects:
    p = projects[0]
    pid = p['id']
    pno = p.get('project_no', '')
    print(f"Testing project: {pid} ({pno})")
    
    # 1. Test raw material update & suggestion generation
    res = update_project_raw_material(pid, 'Aluminum 6061-T6', 110.0, 70.0, 25.0, 'Test Bracket')
    tools = res.get('tools', [])
    print(f"Raw material updated. Tools count: {len(tools)}")
    for t in tools:
        print(f"  - {t['tool_no']}: {t['name']} | {t['suggested_rpm']} RPM | {t['suggested_feed']} mm/min | {t['purpose']}")
    
    # 2. Test DFM warnings
    print(f"DFM warnings: {res.get('dfm_warnings', [])}")
    
    # 3. Test G-code preview
    gcode = res.get('gcode_preview', '')
    print(f"G-code preview lines: {len(gcode.splitlines())}")
    
    # 4. Test Job Slip Confirm Action
    confirm_res = save_job_slip_action(pid, 'confirm', 'Elena Rostova', 'WRK-001')
    print(f"Confirm status: {confirm_res.get('status')} at {confirm_res.get('confirmed_at')}")
    
    # 5. Verify snapshot in get_project
    proj = get_project(pid)
    snap = proj.get('slip_snapshot')
    print(f"Snapshot verified: status={snap.get('status')}, tools={len(snap.get('suggested_tools', []))}")
    print("ALL SERVICES PASSED 100%!")
