# Mathematical and Algorithmic Methods

This document details the exact mathematical formulations, topological algorithms, confidence scoring rules, DFM manufacturability evaluation, tool scoring engine, and cycle time estimation models implemented in the CAD-to-CNC Optimization Engine.

---

## 1. B-Rep Topology and Dihedral Edge Convexity

### 1.1 Edge Convexity Determination
Given two adjacent faces $F_1$ and $F_2$ sharing a B-Rep edge $E$:
1. At parameter midpoint $u = (u_{\min} + u_{\max})/2$ along edge $E$, compute the unit tangent vector $\vec{t}_E = \frac{d\vec{C}(u)}{du} / \left\|\frac{d\vec{C}(u)}{du}\right\|$.
2. At the corresponding surface coordinates $(u_1, v_1)$ on face $F_1$, evaluate the outward unit surface normal $\vec{n}_1$.
3. Compute the in-plane inward normal pointing into $F_1$:
   $$\vec{v}_{\text{in}} = \vec{t}_E \times \vec{n}_1$$
4. Evaluate the dot product with the outward normal $\vec{n}_2$ of adjacent face $F_2$:
   $$c = \vec{v}_{\text{in}} \cdot \vec{n}_2$$
5. Classification:
   - **Concave** (Internal Corner): $c > +0.05$
   - **Convex** (External Corner): $c < -0.05$
   - **Smooth / Tangent**: $|c| \le 0.05$

---

## 2. Feature Recognition Algorithms

### 2.1 Hole vs Boss Solid Classification
For cylindrical surface $S(u, v) = \vec{P}_0 + r(\cos\theta \vec{u} + \sin\theta \vec{v}) + z \vec{w}$:
1. Outward normal is evaluated from the face orientation.
2. An analytical test point is cast slightly into the cylinder radial interior:
   $$\vec{P}_{\text{test}} = \vec{P}_{\text{surf}} - 0.5 \cdot \vec{n}$$
3. Using `BRepClass3d_SolidClassifier`:
   - If $\vec{P}_{\text{test}}$ is `TopAbs_OUT`, the cylinder interior is void and material surrounds it $\implies$ **Hole**.
   - If $\vec{P}_{\text{test}}$ is `TopAbs_IN`, the cylinder interior is solid metal $\implies$ **External Boss/Shaft** (Rejected from hole list).

### 2.2 Hole Types Classification
- **Through Hole**: Both cylinder circular bounds are shared with adjacent planar/outer faces, and no capping planar face closes either end along the axis.
- **Blind Hole (Flat Bottom)**: Closed at one axial extremity by a perpendicular planar face whose outward normal opposes the cylinder axis ($\vec{n}_{\text{floor}} \cdot \vec{a} \approx -1.0$).
- **Blind Hole (Drill Point)**: Closed at one axial extremity by a conical face whose apex points into the material. Cone half-angle $\theta_c$ yields the drill point angle $\alpha = 2(90^\circ - \theta_c)$ (typically $118^\circ$ or $140^\circ$).
- **Counterbore**: Coaxial cylindrical face of larger diameter $D_{\text{cb}} > D_0$ connected to the primary bore via an annular planar transition face.
- **Countersink**: Coaxial conical chamfer face at the hole opening with opening angle $\alpha \approx 82^\circ - 90^\circ$.

### 2.3 Pocket and Slot Distinction
- **Pocket Floor**: Planar face with normal pointing towards an accessible approach direction ($\vec{n} = [0, 0, 1]$ for top setup). All peripheral boundary edges connecting floor to surrounding wall faces must be **concave** ($c > 0.05$).
- **Aspect Ratio Priority**:
  $$\text{Aspect Ratio} = \frac{\text{Length}}{\text{Width}}$$
  - If $\text{Aspect Ratio} \ge 2.5$ and opposing parallel vertical walls enclose the channel $\implies$ classified as **Slot**.
  - If $\text{Aspect Ratio} < 2.5$ with closed or partially open periphery $\implies$ classified as **Pocket**.

### 2.4 Internal Corner Radii and Sharp Corner Detection
Vertical edges connecting pocket wall faces:
- **Sharp Corner**: Straight concave edge shared between two planar wall faces where no cylindrical fillet face exists ($r = 0$).
  - *Manufacturability limitation*: Round rotating cutters of radius $R_c > 0$ cannot machine an inner square corner without leaving uncut fillet material $R_{\min} = R_c$.
- **Filleted Corner**: Cylindrical concave blend face between wall faces. Radius $R_f$ is extracted directly from the cylinder surface curvature.

### 2.5 Thin Wall Detection
For opposing planar wall faces $F_A$ and $F_B$ with opposite outward normals ($\vec{n}_A \cdot \vec{n}_B \approx -1.0$):
1. Compute perpendicular distance:
   $$t = |\vec{n}_A \cdot (\vec{P}_B - \vec{P}_A)|$$
2. Probe midpoint $\vec{P}_{\text{mid}} = (\vec{P}_A + \vec{P}_B)/2$ using `BRepClass3d_SolidClassifier`:
   - If `TopAbs_IN` $\implies$ solid web/rib of thickness $t$.
   - If $t < t_{\min}$ (configured threshold, default $1.5$ mm) $\implies$ flagged as `thin_wall` finding.

---

## 3. Confidence Scoring Formulation

Confidence scores represent rule agreement across geometric sanity checks:
$$\text{Confidence} = \max\left(0.1, 1.0 - \sum \text{Penalties}\right)$$

### Hole Confidence Penalties:
- Base score: $1.0$
- Split cylinder segments requiring stitching: $-0.05$
- Incomplete angular sweep ($< 350^\circ$): $-0.30$
- Tiny diameter ($< 1.0$ mm): $-0.20$
- High aspect ratio ($L/D > 8.0$): $-0.15$
- Non-standard cone point angle ($|\alpha - 118^\circ| > 5^\circ$ and $|\alpha - 140^\circ| > 5^\circ$): $-0.10$

---

## 4. DFM Manufacturability Scoring

The overall manufacturability score is a transparent weighted formula:
$$\text{DFM Score} = \max\left(0.0, 100.0 - 25.0 \cdot N_{\text{red}} - 5.0 \cdot N_{\text{yellow}}\right)$$
Where:
- $N_{\text{red}}$: Number of Red blocker findings (e.g. inaccessible features, out-of-travel envelope, zero compatible tools).
- $N_{\text{yellow}}$: Number of Yellow warning findings (e.g. sharp internal corners, thin walls, deep peck drilling ratios).
- Green findings: Informational confirmations ($0$ point deduction).

---

## 5. Tool Selection and Candidate Scoring

For each feature, compatible tools from the database are scored across 6 weighted criteria:
$$\text{Score} = w_d \cdot S_{\text{diam}} + w_m \cdot S_{\text{mat}} + w_r \cdot S_{\text{reach}} + w_o \cdot S_{\text{op}} + w_e \cdot S_{\text{eff}}$$
Weights (configured):
- Diameter match ($w_d = 0.35$): Exact match for drills yields $1.0$. For end mills, tool diameter $\le 0.8 \times \text{pocket width}$ scores highest.
- Material compatibility ($w_m = 0.25$): $1.0$ if workpiece material in tool's `compatible_materials`, else tool rejected.
- Reach sufficiency ($w_r = 0.20$): $1.0$ if flute length $\ge$ feature depth. If overall reach $\ge$ depth but flute length $<$ depth, penalized to $0.6$. If reach $<$ depth, rejected.
- Operation suitability ($w_o = 0.10$): $1.0$ if operation type in tool's supported operations.
- Spindle efficiency ($w_e = 0.10$): Larger diameter within safe bounds scores higher to maximize material removal rate (MRR).

---

## 6. Optimization and Cycle Time Estimation

### 6.1 Cycle Time Components
$$\text{Total Time} = T_{\text{cut}} + T_{\text{rapid}} + T_{\text{tool\_change}} + T_{\text{setup}}$$
Where:
- Linear cut time: $T_{\text{cut}} = \sum \frac{L_i}{F_i}$
- Rapid traverse time: $T_{\text{rapid}} = \frac{D_{\text{rapid}}}{V_{\text{rapid}}}$
- Automatic tool change time: $T_{\text{tool\_change}} = N_{\text{tc}} \times t_{\text{tc\_config}}$
- Setup change time: $T_{\text{setup}} = N_{\text{setups}} \times t_{\text{setup\_config}}$

### 6.2 2-Opt Traveling Salesperson Optimization
Within each tool group, hole and feature locations $(x_k, y_k)$ are ordered by solving the Euclidean Traveling Salesperson Problem (TSP):
1. **Initial Tour**: Nearest-neighbor heuristic starting from the tool change retract origin.
2. **2-Opt Local Search**: Iteratively evaluate pairwise edge swaps $(i, i+1)$ and $(j, j+1)$:
   $$\Delta D = (d_{i, j} + d_{i+1, j+1}) - (d_{i, i+1} + d_{j, j+1})$$
3. If $\Delta D < -10^{-6}$, reverse tour segment $[i+1, j]$. Repeat until no improving 2-opt inversion exists.
