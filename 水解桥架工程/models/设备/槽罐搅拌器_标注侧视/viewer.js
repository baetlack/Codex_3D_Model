(() => {
  const canvas = document.querySelector('#model');
  const gl = canvas.getContext('webgl', { alpha: true, antialias: true });
  if (!gl) {
    document.querySelector('#hint').textContent = '浏览器未启用 WebGL，可下载 GLB 查看。';
    return;
  }

  function shader(type, source) {
    const result = gl.createShader(type);
    gl.shaderSource(result, source);
    gl.compileShader(result);
    if (!gl.getShaderParameter(result, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(result));
    return result;
  }

  const program = gl.createProgram();
  gl.attachShader(program, shader(gl.VERTEX_SHADER, `
    attribute vec3 position, normal, color;
    uniform vec3 horizontal, vertical, towardCamera, center;
    uniform vec2 scale;
    varying vec3 tint, direction;
    void main() {
      vec3 p = position - center;
      gl_Position = vec4(dot(p, horizontal) * scale.x, dot(p, vertical) * scale.y,
                         -dot(p, towardCamera) * 0.0003, 1.0);
      direction = normal;
      tint = color;
    }`));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, `
    precision mediump float;
    varying vec3 tint, direction;
    void main() {
      vec3 n = normalize(direction);
      float key = max(dot(n, normalize(vec3(0.25, -0.6, 0.8))), 0.0);
      float fill = max(dot(n, normalize(vec3(-0.9, 0.5, 0.25))), 0.0);
      gl_FragColor = vec4(tint * (0.60 + 0.46 * key + 0.20 * fill), 1.0);
    }`));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);

  const data = [], ranges = [];
  let low = Infinity, high = -Infinity, span = 0;
  for (const part of window.MODEL_PARTS) {
    const start = data.length / 9;
    const rgb = part.color.slice(1).match(/../g).map(channel => parseInt(channel, 16) / 255);
    part.vertices.forEach(([x, y, z]) => {
      low = Math.min(low, z);
      high = Math.max(high, z);
      span = Math.max(span, Math.hypot(x, y));
    });
    part.faces.forEach((face, index) => {
      for (let i = 1; i < face.length - 1; i++) {
        for (const j of [0, i, i + 1]) {
          data.push(...part.vertices[face[j]], ...part.normals[index][j], ...rgb);
        }
      }
    });
    ranges.push({ group: part.name.slice(0, 2), start, count: data.length / 9 - start });
  }
  const mesh = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, mesh);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW);
  ['position', 'normal', 'color'].forEach((name, index) => {
    const location = gl.getAttribLocation(program, name);
    gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 36, 12 * index);
    gl.enableVertexAttribArray(location);
  });
  const uniforms = Object.fromEntries(['horizontal', 'vertical', 'towardCamera', 'center', 'scale']
    .map(name => [name, gl.getUniformLocation(program, name)]));
  gl.uniform3f(uniforms.center, 0, 0, (low + high) / 2);

  const boxes = [...document.querySelectorAll('input[type=checkbox]')];
  let yaw = -Math.PI / 4, elevation = Math.PI / 9, zoom = 1, drag;
  function draw() {
    const ratio = Math.min(2, devicePixelRatio);
    const width = Math.round(canvas.clientWidth * ratio), height = Math.round(canvas.clientHeight * ratio);
    if (!width || !height) return;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    gl.viewport(0, 0, width, height);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const x = Math.cos(yaw), y = Math.sin(yaw);
    const c = Math.cos(elevation), s = Math.sin(elevation);
    const fit = zoom * Math.min(1.60 * height / (high - low), 0.8 * width / span);
    gl.uniform3f(uniforms.horizontal, -y, x, 0);
    gl.uniform3f(uniforms.vertical, -x * s, -y * s, c);
    gl.uniform3f(uniforms.towardCamera, x * c, y * c, s);
    gl.uniform2f(uniforms.scale, fit / width, fit / height);
    const visible = new Set(boxes.filter(box => box.checked).map(box => box.value));
    ranges.forEach(({ group, start, count }) => {
      if (visible.has(group)) gl.drawArrays(gl.TRIANGLES, start, count);
    });
  }

  canvas.onpointerdown = event => {
    drag = [event.clientX, event.clientY, yaw, elevation];
    canvas.setPointerCapture(event.pointerId);
  };
  canvas.onpointermove = event => {
    if (!drag) return;
    yaw = drag[2] + (event.clientX - drag[0]) * .009;
    elevation = Math.max(0, Math.min(Math.PI / 2, drag[3] + (event.clientY - drag[1]) * .008));
    draw();
  };
  canvas.onlostpointercapture = () => { drag = null; };
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    zoom = Math.max(.4, Math.min(3, zoom * Math.exp(-Math.sign(event.deltaY) * .11)));
    draw();
  }, { passive: false });
  document.querySelector('#side').onclick = () => { yaw = -Math.PI / 2; elevation = 0; zoom = 1; draw(); };
  document.querySelector('#reset').onclick = () => { yaw = -Math.PI / 4; elevation = Math.PI / 9; zoom = 1; draw(); };
  document.querySelector('#drive').onclick = () => { boxes.forEach(box => { box.checked = Number(box.value) <= 5; }); draw(); };
  document.querySelector('#all').onclick = () => { boxes.forEach(box => { box.checked = true; }); draw(); };
  boxes.forEach(box => { box.onchange = draw; });
  new ResizeObserver(draw).observe(canvas);
  draw();
})();
