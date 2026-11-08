/* A GLB reader small enough to trust: parse the container, take the triangles.
 *
 * The scenes run on a vendored `three.module.js` whose revision is not declared,
 * and the only GLTFLoader on this box belongs to three 0.180 — pairing them is a
 * guess. This reads what the bake actually needs (positions, normals, indices)
 * and nothing else: no textures, no skinning, no animation. A scene that wants a
 * surface look supplies its own material.
 *
 * Usage:  const meshes = await loadGLB('./data/meshy/daydream/mug.glb')
 *         meshes.mergeInto(sceneMaterial) -> THREE.Group
 */

export async function loadGLB(url, THREE, material) {
  const buf = new Uint8Array(await (await fetch(url)).arrayBuffer());
  const view = new DataView(buf.buffer);
  const magic = view.getUint32(0, true);
  if (magic !== 0x46546c67) throw new Error(`${url}: not a GLB (magic ${magic.toString(16)})`);
  let offset = 12;
  let json = null;
  let bin = null;
  while (offset < buf.byteLength) {
    const len = view.getUint32(offset, true);
    const type = view.getUint32(offset + 4, true);
    const start = offset + 8;
    if (type === 0x4e4f534a) {
      json = JSON.parse(new TextDecoder().decode(buf.subarray(start, start + len)));
    } else if (type === 0x004e4942) {
      bin = buf.subarray(start, start + len);
    }
    offset = start + len + ((4 - (len % 4)) % 4);
  }
  if (!json || !bin) throw new Error(`${url}: GLB is missing its JSON or BIN chunk`);

  const components = { 5120: Int8Array, 5121: Uint8Array, 5122: Int16Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
  const widths = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };

  function readAccessor(index) {
    const acc = json.accessors[index];
    const bv = json.bufferViews[acc.bufferView];
    const Type = components[acc.componentType];
    if (!Type) throw new Error(`${url}: unsupported componentType ${acc.componentType}`);
    const width = widths[acc.type];
    const start = (bv.byteOffset || 0) + (acc.byteOffset || 0);
    const count = acc.count * width;
    const stride = bv.byteStride;
    if (stride && stride !== width * Type.BYTES_PER_ELEMENT) {
      // interleaved: copy element by element
      const out = new Type(count);
      const esize = Type.BYTES_PER_ELEMENT;
      const dv = new DataView(bin.buffer, bin.byteOffset);
      for (let i = 0; i < acc.count; i++) {
        for (let c = 0; c < width; c++) {
          const at = start + i * stride + c * esize;
          out[i * width + c] = Type === Float32Array ? dv.getFloat32(at, true)
            : Type === Uint32Array ? dv.getUint32(at, true)
            : Type === Uint16Array ? dv.getUint16(at, true)
            : Type === Int16Array ? dv.getInt16(at, true)
            : Type === Int8Array ? dv.getInt8(at)
            : dv.getUint8(at);
        }
      }
      return out;
    }
    return new Type(bin.buffer, bin.byteOffset + start, count);
  }

  const group = new THREE.Group();
  group.name = url;

  (json.meshes || []).forEach((mesh) => {
    (mesh.primitives || []).forEach((prim) => {
      if (prim.mode !== undefined && prim.mode !== 4) return; // triangles only
      const position = prim.attributes.POSITION;
      const normal = prim.attributes.NORMAL;
      if (position === undefined) return;
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(readAccessor(position), 3));
      if (normal !== undefined) geo.setAttribute('normal', new THREE.BufferAttribute(readAccessor(normal), 3));
      else geo.computeVertexNormals();
      if (prim.indices !== undefined) {
        const idx = readAccessor(prim.indices);
        geo.setIndex(new THREE.BufferAttribute(idx instanceof Uint32Array ? idx : new Uint16Array(idx), 1));
      }
      const object = new THREE.Mesh(geo, material);
      group.add(object);
    });
  });

  if (!group.children.length) throw new Error(`${url}: no triangle primitives`);
  return group;
}
