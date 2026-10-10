# Third-Party Licenses and Open Source Attribution

This document records all third-party libraries, toolkits, and dependencies used in the **Automated CAD-to-CNC Optimization Engine (cad-cnc-engine)**. All components are strictly open-source, compliant with hackathon and commercial distribution guidelines.

---

## Dependency License Matrix

| Library | Version | License | Official URL / Repository | Role in Engine | Limitations & License Obligations |
|---|---|---|---|---|---|
| **cadquery-ocp** | 7.9.3.1.1 | LGPL-2.1 with OCCT Exception | [github.com/CadQuery/OCP](https://github.com/CadQuery/OCP) | Python C++ bindings for Open CASCADE Technology (OCCT). B-Rep topology traversal, geometric surface analysis, surface normal evaluation, solid classification. | LGPL-2.1 with Exception allows dynamic linking without forcing copyleft on application code. Prebuilt binary wheels on PyPI support Windows x64. |
| **cadquery** | 2.8.0 | Apache-2.0 | [github.com/CadQuery/cadquery](https://github.com/CadQuery/cadquery) | Synthetic parametric CAD test model generation with verified ground-truth features. | Used strictly for developer test generation and benchmarks; not embedded into customer production runtime paths. |
| **shapely** | 2.2.0 | BSD-3-Clause | [github.com/shapely/shapely](https://github.com/shapely/shapely) | 2D computational geometry: polygon offsetting, polygon intersection, pocket clearing toolpath generation, oriented bounding rectangles. | 2D planar geometry only; cannot process 3D curved surfaces directly. |
| **pyclipper** | 1.4.0 | MIT | [github.com/fonttools/pyclipper](https://github.com/fonttools/pyclipper) | Clipper library wrapper for robust polygon clipping and multi-contour offsetting for roughing pocket clearing passes. | Integer-coordinate based under the hood; requires float-to-int coordinate scaling factors for micro-inch or sub-micron precision. |
| **pydantic** | 2.14.0 | MIT | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic) | Robust data contract schemas, type validation, JSON serialization and deserialization with `schema_version`. | V2 Rust-core; strict typing prevents silent type conversions. |
| **pyyaml** | 6.0.3 | MIT | [github.com/yaml/pyyaml](https://github.com/yaml/pyyaml) | Parsing human-readable YAML configuration files (machine limits, thresholds). | Standard YAML 1.1 parser; does not preserve key ordering in older Python dictionaries without special loaders. |
| **numpy** | 2.4.6 | BSD-3-Clause | [github.com/numpy/numpy](https://github.com/numpy/numpy) | Vector maths, matrix transformations, coordinate rotation, 2-opt Euclidean distance calculations. | Permissive BSD license. |
| **scipy** | 1.17.1 | BSD-3-Clause | [github.com/scipy/scipy](https://github.com/scipy/scipy) | Spatial algorithms (KD-trees, convex hulls) and optimization calculations. | Permissive BSD license. |
| **trimesh** | 5.1.1 | MIT | [github.com/mikedh/trimesh](https://github.com/mikedh/trimesh) | Lightweight 3D mesh export (GLB / STL) for Phase 2 web visualization previews. | Mesh representation loses precise B-Rep analytical continuity (edges become faceted triangles). Never used for feature detection. |
| **pytest** | 9.1.1 | MIT | [github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest) | Unit, integration, regression, and known-answer test suites. | Test runner only. |
| **fastapi** | 0.143.0 | MIT | [github.com/fastapi/fastapi](https://github.com/fastapi/fastapi) | High-performance async web framework for REST and WebSocket endpoints. | Permissive MIT license. |
| **uvicorn** | 0.54.0 | BSD-3-Clause | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) | ASGI web server implementation. | Permissive BSD license. |
| **sqlalchemy** | 2.1.4 | MIT | [github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | SQL toolkit and Object Relational Mapper (ORM). | Permissive MIT license. |
| **alembic** | 1.20.0 | MIT | [github.com/sqlalchemy/alembic](https://github.com/sqlalchemy/alembic) | Database migration tool for SQLAlchemy. | Permissive MIT license. |
| **pyjwt** | 2.15.1 | MIT | [github.com/jpadilla/pyjwt](https://github.com/jpadilla/pyjwt) | RFC 7519 JSON Web Token implementation. | Permissive MIT license. |
| **argon2-cffi** | 25.1.0 | MIT | [github.com/hynek/argon2-cffi](https://github.com/hynek/argon2-cffi) | Secure password hashing using Argon2 algorithm. | Permissive MIT license. |
| **passlib** | 1.7.4 | BSD | [foss.heptapod.net/python-libs/passlib](https://foss.heptapod.net/python-libs/passlib) | Password hashing framework. | Permissive BSD license. |
| **opencv-python-headless** | 5.0.0.93 | Apache-2.0 | [github.com/opencv/opencv-python](https://github.com/opencv/opencv-python) | Computer vision contour and edge detection for 2.5D extrusion. | Permissive Apache-2.0 license. |
| **pydantic-settings** | 2.15.0 | MIT | [github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) | Typed configuration and environment settings loading. | Permissive MIT license. |
| **react** | 19.2.8 | MIT | [github.com/facebook/react](https://github.com/facebook/react) | Frontend UI component library. | Permissive MIT license. |
| **vite** | 8.3.4 | MIT | [github.com/vitejs/vite](https://github.com/vitejs/vite) | Frontend build tool and development server. | Permissive MIT license. |
| **tailwindcss** | 4.3.3 | MIT | [github.com/tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) | Utility-first CSS styling engine. | Permissive MIT license. |
| **three** | 0.186.1 | MIT | [github.com/mrdoob/three.js](https://github.com/mrdoob/three.js) | WebGL 3D rendering library. | Permissive MIT license. |
| **@react-three/fiber** | 9.8.1 | MIT | [github.com/pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber) | React renderer for Three.js. | Permissive MIT license. |
| **@react-three/drei** | 10.7.9 | MIT | [github.com/pmndrs/drei](https://github.com/pmndrs/drei) | Helpers and primitives for react-three-fiber. | Permissive MIT license. |
| **framer-motion** | 14.0.0 | MIT | [github.com/motiondivision/motion](https://github.com/motiondivision/motion) | Animation library for React. | Permissive MIT license. |
| **zustand** | 5.0.15 | MIT | [github.com/pmndrs/zustand](https://github.com/pmndrs/zustand) | Lightweight global state management for React. | Permissive MIT license. |
| **@tanstack/react-query** | 5.104.1 | MIT | [github.com/tanstack/query](https://github.com/tanstack/query) | Async state and server data caching library. | Permissive MIT license. |
| **react-router-dom** | 7.18.4 | MIT | [github.com/remix-run/react-router](https://github.com/remix-run/react-router) | Declarative client-side routing for React. | Permissive MIT license. |
| **lucide-react** | 1.54.0 | ISC | [github.com/lucide-icons/lucide](https://github.com/lucide-icons/lucide) | Modern icon library for React. | Permissive ISC license. |
| **recharts** | 3.10.1 | MIT | [github.com/recharts/recharts](https://github.com/recharts/recharts) | Composable charting library for React. | Permissive MIT license. |
| **@dnd-kit/core** | 6.3.1 | MIT | [github.com/clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) | Drag and drop toolkit for React. | Permissive MIT license. |
| **zod** | 3.25.76 | MIT | [github.com/colinhacks/zod](https://github.com/colinhacks/zod) | TypeScript-first schema declaration and validation. | Permissive MIT license. |

---

## License Compliance Considerations

1. **Open CASCADE Technology (OCCT) / OCP (LGPL-2.1 with Exception)**:
   - The OCCT license explicitly permits linking proprietary or non-copyleft software with OCCT libraries without requiring the proprietary source code to be disclosed.
   - We distribute and invoke `cadquery-ocp` as dynamically loaded shared libraries/wheels.
2. **GPL Tool Isolation**:
   - No GPL-licensed components are bundled or statically linked into the core engine.
   - FreeCAD Path/CAM is GPL-2.0+ and was evaluated in research; as detailed in `docs/RESEARCH.md`, we intentionally chose an internal 2D offset generator (using MIT/BSD Shapely & Pyclipper) to keep our engine standalone, lightweight, headless, and free from GPL viral obligations.
3. **Apache 2.0 / MIT / BSD**:
   - All other runtime libraries (Pydantic, PyYAML, NumPy, SciPy, Shapely, Pyclipper, Trimesh) use permissive non-copyleft licenses suitable for hackathon, educational, and commercial utilization.
