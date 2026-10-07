// Colors used to overlay segmentation labels.
const colors = [
  null, "#ef4444", "#3b82f6", "#fb923c", "#22d3ee",
  "#facc15", "#a78bfa", "#34d399", "#f472b6"
];
const structureNames = {
  1: "Left ventricle",
  2: "Right ventricle",
  3: "Left atrium",
  4: "Right atrium",
  5: "Aorta",
  6: "Pulmonary artery",
  7: "Superior vena cava",
  8: "Inferior vena cava"
};
const caseDescription =
  "Static 3D MRI; slice playback does not represent a beating heart.";

// Initialize the canvases, controls, and current viewer state.
const canvas = document.getElementById("scan");
const ctx = canvas.getContext("2d");
const scratch = document.createElement("canvas");
const scratchCtx = scratch.getContext("2d", {willReadFrequently: true});
const slider = document.getElementById("slice");
const overlay = document.getElementById("overlay");

let data;
let plane = "axial";
let frame = 0;
let timer = null;
let selected = 0;
let images = {};
let base = "data/";
let comparisonCases = [];

// Load images and switch planes, loading each image pair only once.
function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = url;
  });
}

async function choosePlane(name) {
  stop();
  plane = name;
  document.querySelectorAll("[data-plane]").forEach(button => {
    button.classList.toggle("active", button.dataset.plane === name);
  });
  if (!images[name]) {
    images[name] = await Promise.all([
      loadImage(base + data.planes[name].image),
      loadImage(base + data.planes[name].labels)
    ]);
  }
  frame = Math.floor(data.planes[name].count / 2);
  slider.max = data.planes[name].count - 1;
  slider.value = frame;
  drawSlice();
}

// Draw the current MRI slice and overlay the selected segmentation labels.
function drawSlice() {
  const info = data.planes[plane];
  const pair = images[plane];
  if (!pair) return;
  const sourceX = (frame % info.columns) * info.width;
  const sourceY = Math.floor(frame / info.columns) * info.height;
  canvas.width = info.width;
  canvas.height = info.height;
  ctx.drawImage(pair[0], sourceX, sourceY, info.width, info.height,
                0, 0, info.width, info.height);

  if (overlay.checked) {
    scratch.width = info.width;
    scratch.height = info.height;
    scratchCtx.drawImage(pair[1], sourceX, sourceY,
      info.width, info.height, 0, 0, info.width, info.height);
    const pixels = scratchCtx.getImageData(0, 0, info.width, info.height);
    for (let index = 0; index < pixels.data.length; index += 4) {
      const label = pixels.data[index];
      if (label > 0 && (selected === 0 || selected === label)) {
        const hex = colors[label];
        pixels.data[index] = parseInt(hex.slice(1, 3), 16);
        pixels.data[index + 1] = parseInt(hex.slice(3, 5), 16);
        pixels.data[index + 2] = parseInt(hex.slice(5, 7), 16);
        pixels.data[index + 3] = 120;
      } else {
        pixels.data[index + 3] = 0;
      }
    }
    scratchCtx.putImageData(pixels, 0, 0);
    ctx.drawImage(scratch, 0, 0);
  }

  document.getElementById("slice-stamp").textContent =
    `${data.case_id} • ${frame + 1}/${info.count} • ` +
    `${(frame * info.spacing).toFixed(1)} mm`;
  document.getElementById("orientation").textContent =
    `Orientation: ${info.marks.join(" / ")}`;
}

  // Update the 3D model and synchronize the selected structure across the interface.
function drawModel() {
  const traces = data.structures.map(part => ({
    type: "mesh3d", name: part.name,
    x: part.x, y: part.y, z: part.z,
    i: part.i, j: part.j, k: part.k,
    color: part.color, opacity: 0.86,
    visible: selected === 0 || selected === part.id,
    hovertemplate: `${part.name}<br>${part.volume_ml} mL<extra></extra>`
  }));
  Plotly.react("plot", traces, {
    margin: {l: 0, r: 0, t: 0, b: 0}, showlegend: false,
    scene: {aspectmode: "data", xaxis: {visible: false},
      yaxis: {visible: false}, zaxis: {visible: false}}
  }, {responsive: true, displaylogo: false});
  document.querySelectorAll(".part").forEach(button => {
    button.classList.toggle("selected", selected === Number(button.dataset.id));
  });
  document.querySelectorAll(".measurement-row").forEach(row => {
    row.classList.toggle("selected", selected === Number(row.dataset.id));
  });
  drawSlice();
}

// Build the voxel count, volume, and size table for each structure.
function renderMeasurements() {
  const body = document.getElementById("measurements");
  body.replaceChildren();
  data.structures.forEach(part => {
    const row = document.createElement("tr");
    row.className = "measurement-row";
    row.dataset.id = part.id;
    row.innerHTML = `
      <td><span class="dot" style="display:inline-block;background:${part.color}"></span>
          ${part.name}</td>
      <td>${part.voxel_count.toLocaleString("en-US")}</td>
      <td>${part.volume_ml.toFixed(2)} mL</td>
      <td>${part.size_mm.map(value => value.toFixed(1)).join(" × ")} mm</td>`;
    row.onclick = () => {
      selected = selected === part.id ? 0 : part.id;
      drawModel();
    };
    body.appendChild(row);
  });
}

// Populate the structure selector and volume comparison chart.
function fillCompareOptions() {
  const select = document.getElementById("compare-structure");
  select.replaceChildren();
  data.structures.forEach(part => {
    const option = document.createElement("option");
    option.value = part.id;
    option.textContent = part.name;
    select.appendChild(option);
  });
  select.value = String(data.structures[0]?.id || 1);
  select.onchange = drawComparison;
  drawComparison();
}

// Filter for the selected structure and render the comparison chart.
function drawComparison() {
  const labelId = Number(document.getElementById("compare-structure").value);
  if (!labelId) return;
  const rows = comparisonCases.map(item => ({
    caseId: item.case_id,
    part: item.structures.find(part => part.id === labelId)
  })).filter(row => row.part);
  const active = data.structures.find(part => part.id === labelId);
  Plotly.react("comparison", [{
    type: "bar",
    x: rows.map(row => row.caseId),
    y: rows.map(row => row.part.volume_ml),
    marker: {color: rows.map(row =>
      row.caseId === data.case_id ? active.color : "#9db7bb")},
    text: rows.map(row => `${row.part.volume_ml.toFixed(2)} mL`),
    textposition: "outside", cliponaxis: false
  }], {
    margin: {l: 55, r: 15, t: 15, b: 45},
    yaxis: {title: "Volume (mL)", rangemode: "tozero"},
    xaxis: {title: "Heart case"}, showlegend: false
  }, {responsive: true, displaylogo: false});
}

// Stop the slice playback timer.
function stop() {
  if (timer) clearInterval(timer);
  timer = null;
  document.getElementById("play").textContent = "▶ Play slices";
}

// Handle slice playback, navigation, plane changes, and structure selection.
document.getElementById("play").onclick = () => {
  if (timer) { stop(); return; }
  document.getElementById("play").textContent = "Ⅱ Pause";
  timer = setInterval(() => {
    frame = (frame + 1) % data.planes[plane].count;
    slider.value = frame;
    drawSlice();
  }, 125);
};
slider.oninput = () => { stop(); frame = Number(slider.value); drawSlice(); };
overlay.onchange = drawSlice;
document.querySelectorAll("[data-plane]").forEach(button => {
  button.onclick = () => choosePlane(button.dataset.plane);
});
document.getElementById("show-all").onclick = () => {
  selected = 0; drawModel();
};
document.getElementById("reset").onclick = () => Plotly.relayout(
  "plot", {"scene.camera": {eye: {x: 1.4, y: 1.4, z: 1.1}}}
);

// Load case data and build the structure list for the viewer.
function loadCase(folder) {
  stop();
  base = folder;
  images = {};
  selected = 0;
  fetch(base + "case.json").then(response => response.json()).then(caseData => {
    data = caseData;
    data.description = caseDescription;
    data.structures.forEach(part => {
      part.name = structureNames[part.id] || part.name;
    });
    document.getElementById("case-summary").textContent =
      `${data.case_id} • ${data.shape.join(" × ")} voxel • ${data.description}`;
    const parts = document.getElementById("parts");
    parts.replaceChildren();
    data.structures.forEach(part => {
      const button = document.createElement("button");
      button.className = "part";
      button.dataset.id = part.id;
      button.innerHTML = `<span class="dot" style="background:${part.color}"></span>` +
        `<span>${part.name} • ${part.volume_ml} mL</span>`;
      button.onclick = () => {
        selected = selected === part.id ? 0 : part.id;
        drawModel();
      };
      parts.appendChild(button);
    });
    renderMeasurements();
    fillCompareOptions();
    drawModel();
    choosePlane("axial");
  });
}

// Load the case catalog, comparison data, and case selector options.
const caseSelect = document.getElementById("case-select");
caseSelect.onchange = () => loadCase(caseSelect.value);
fetch("cases.json").then(response => response.ok ? response.json() : [])
  .then(async items => {
    items.forEach(item => {
      if ([...caseSelect.options].some(option => option.text === item.case_id)) return;
      const option = document.createElement("option");
      option.text = item.case_id;
      option.value = item.base;
      caseSelect.add(option);
    });
    comparisonCases = await Promise.all(items.map(item =>
      fetch(item.base + "case.json").then(response => response.json())
    ));
    drawComparison();
  }).catch(() => {});

// Load the default case when the page opens.
loadCase("cases/pat1/data/");

