function imageToHeightGrid(image, gridSize = 56) {
  const canvas = document.createElement("canvas");
  canvas.width = gridSize;
  canvas.height = gridSize;
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(image, 0, 0, gridSize, gridSize);
  const { data } = ctx.getImageData(0, 0, gridSize, gridSize);

  const lum = new Float32Array(gridSize * gridSize);
  let sum = 0;
  for (let i = 0; i < lum.length; i++) {
    const l = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2];
    lum[i] = l;
    sum += l;
  }
  const mean = sum / lum.length;
  let darkerCount = 0;
  for (let i = 0; i < lum.length; i++) if (lum[i] < mean) darkerCount++;
  const objectIsDark = darkerCount < lum.length / 2;

  const grid = new Float32Array(gridSize * gridSize);
  let max = 0.0001;
  for (let i = 0; i < lum.length; i++) {
    let v = objectIsDark ? mean - lum[i] : lum[i] - mean;
    v = Math.max(0, v);
    grid[i] = v;
    if (v > max) max = v;
  }
  for (let i = 0; i < grid.length; i++) grid[i] = grid[i] / max;

  const edgeCells = [];
  for (let y = 1; y < gridSize - 1; y++) {
    for (let x = 1; x < gridSize - 1; x++) {
      const i = y * gridSize + x;
      const gx = grid[i + 1] - grid[i - 1];
      const gy = grid[i + gridSize] - grid[i - gridSize];
      const mag = Math.sqrt(gx * gx + gy * gy);
      if (mag > 0.3) edgeCells.push({ x, y, mag });
    }
  }
  edgeCells.sort((a, b) => b.mag - a.mag);

  return { grid: Array.from(grid), gridSize, edgeCells };
}

if (typeof window !== "undefined") {
  window.imageToHeightGrid = imageToHeightGrid;
}
