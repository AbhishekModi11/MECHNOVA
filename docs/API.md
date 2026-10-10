# Mechnova CAD-to-CNC Platform: REST & WebSocket API Documentation

All API routes are served under prefix `/api` (except WebSocket under `/ws`). Authentication uses standard HTTP Bearer JWT tokens.

---

## 1. Authentication & Identity

### `POST /api/auth/login`
Authenticates a user against Argon2 hashed credentials and validates role tab alignment.
- **Request Body**:
  ```json
  {
    "email": "elena@mechnova.com",
    "password": "worker123",
    "role_tab": "worker"
  }
  ```
- **Responses**:
  - `200 OK`: Returns JWT access token and user metadata.
  - `401 Unauthorized`: Invalid email or incorrect password.
  - `403 Forbidden`: Role tab mismatch (e.g., worker attempting login on the admin tab).

### `GET /api/me`
Retrieves profile of the currently authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK` with user details.

---

## 2. Worker Projects & CAD Optimization

### `POST /api/projects`
Uploads a STEP CAD model or reference 2D image and queues background analysis.
- **Headers**: `Authorization: Bearer <token>`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `name`: String
  - `material_id`: String (e.g., `aluminum_6061`)
  - `source_type`: `"step"` or `"image_extrusion"`
  - `target_width_mm`: Float
  - `extrusion_height_mm`: Float
  - `file`: Binary file upload (`.step`, `.stp`, `.png`, `.jpg`)

### `GET /api/projects`
Lists projects owned by current user (or all projects if requested by Admin).

### `GET /api/projects/{id}`
Returns status, bounding box dimensions, and lifecycle state.

### `POST /api/projects/{id}/analyse`
Manually triggers or re-runs the CAD-to-CNC Optimization Engine pipeline.

### `GET /api/projects/{id}/model`
Serves the generated GLB 3D tessellation file for Three.js rendering.
- **Content-Type**: `model/gltf-binary`

### `GET /api/projects/{id}/features`
Returns recognized topological manufacturing features (holes, pockets, slots, corners).

### `GET /api/projects/{id}/tools`
Returns recommended cutting tools, qualification reasons, and suitability scores.

### `GET /api/projects/{id}/plan`
Returns operation sequencing, cycle time estimates, and baseline vs optimized comparison.

### `GET /api/projects/{id}/report`
Serves the engineering analysis report (`report.html` or `report.md`).

### `GET /api/projects/{id}/gcode`
Serves validated prototype G-code program with non-production safety disclaimer.

### `PATCH /api/projects/{id}/dimensions`
Updates stock dimensions.

### `PATCH /api/projects/{id}/material`
Updates target workpiece material (validates against supported alloys).

### `POST /api/projects/{id}/check-tools`
Executes heuristic cutting wear evaluation, flags worn tools, and automatically swaps in fresh spares.

### `POST /api/projects/{id}/request-machine`
Submits a formal job dispatch request to shop administrators.

### `POST /api/projects/{id}/deploy`
Deploys an approved job and initiates simulated spindle execution.

### `GET /api/projects/{id}/progress`
Returns live simulated progression (`progress_percent`, `current_operation`).

---

## 3. Shop Administration & Fleet Management

### `GET /api/admin/machines/summary`
Returns fleet KPI cards, working/idle counts, and active machine cards.

### `GET /api/admin/workers`
Returns all registered operators, today's attendance status, and active machine assignments.

### `GET /api/admin/workers/{id}`
Returns operator's 90-day attendance metrics and project history.

### `GET /api/admin/requests`
Lists pending machine requests with estimated cycle times from the core engine.

### `POST /api/admin/requests/{id}/approve`
Approves a dispatch request and reserves a conflict-free machine schedule slot.
- **Response `409 Conflict`**: Returned if the slot overlaps with an existing reservation, providing a suggested next free slot.

### `POST /api/admin/requests/{id}/reject`
Rejects a request with an explanation reason note.

### `GET /api/admin/schedule`
Returns timeline reservations for all CNC stations.

---

## 4. Tool Stock & Notifications

### `GET /api/tools/stock`
Returns all spindle and crib cutters with life used, total life, and change history.

### `GET /api/notifications`
Returns unread notifications for the user.

### `PATCH /api/notifications/{id}/read`
Marks notification as read.

---

## 5. WebSockets

### `WebSocket /ws/projects/{project_id}`
Streams live engine pipeline updates and simulated machining execution steps:
```json
{
  "project_id": 1,
  "stage": "machining_simulation",
  "percent": 45.2,
  "message": "[Simulated] Feature Pocketing in progress (45.2%)",
  "extra": {
    "current_operation": "Feature Pocketing",
    "simulated": true
  }
}
```
