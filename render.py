# render.py — GOAL SURVIVOR 네온 인트로 (5초, 720p, MP4)
# 실행: blender -b --factory-startup -P render.py
import bpy
import os
import math

# ---------- 기본 설정 ----------
FPS = 24
DURATION_SEC = 30
FRAME_END = FPS * DURATION_SEC          # 120 프레임
TEXT = "GOAL SURVIVOR"                   # 원하는 문구로 변경
NEON_CYAN = (0.0, 0.9, 1.0, 1.0)
NEON_MAGENTA = (1.0, 0.1, 0.8, 1.0)

scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END

# 기존 오브젝트 전부 삭제
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ---------- 월드 (거의 검은 배경) ----------
world = bpy.data.worlds.new("NeonWorld")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.002, 0.006, 1)

# ---------- 머티리얼 헬퍼 ----------
def emission_mat(name, color, strength=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in nt.nodes:
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emi = nt.nodes.new('ShaderNodeEmission')
    emi.inputs['Color'].default_value = color
    emi.inputs['Strength'].default_value = strength
    nt.links.new(emi.outputs['Emission'], out.inputs['Surface'])
    return mat, emi

def glossy_floor_mat():
    mat = bpy.data.materials.new("Floor")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.01, 0.01, 0.02, 1)
    bsdf.inputs['Metallic'].default_value = 0.9
    bsdf.inputs['Roughness'].default_value = 0.15
    return mat

# ---------- 바닥 (반사판) ----------
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -1.2))
floor = bpy.context.object
floor.data.materials.append(glossy_floor_mat())

# ---------- 네온 텍스트 ----------
bpy.ops.object.text_add(location=(0, 0, 0))
txt = bpy.context.object
txt.data.body = TEXT
txt.data.align_x = 'CENTER'
txt.data.align_y = 'CENTER'
txt.data.extrude = 0.06
txt.data.bevel_depth = 0.01
txt.data.size = 1.0
txt.rotation_euler = (math.radians(90), 0, 0)  # 세워서 카메라를 향하게
mat_text, emi_text = emission_mat("NeonText", NEON_CYAN, 4.0)
txt.data.materials.append(mat_text)

# 텍스트 발광 펄스 애니메이션 (4 -> 10 -> 4)
s = emi_text.inputs['Strength']
s.default_value = 4.0
s.keyframe_insert('default_value', frame=1)
s.default_value = 10.0
s.keyframe_insert('default_value', frame=FRAME_END // 2)
s.default_value = 4.0
s.keyframe_insert('default_value', frame=FRAME_END)

# ---------- 회전하는 네온 링 2개 ----------
def make_ring(name, color, radius, axis):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius, minor_radius=0.035, location=(0, 0, 0))
    ring = bpy.context.object
    ring.name = name
    mat, _ = emission_mat(name + "Mat", color, 8.0)
    ring.data.materials.append(mat)
    # 한 바퀴 회전 (선형 보간으로 등속)
    ring.rotation_euler = (0, 0, 0)
    ring.keyframe_insert('rotation_euler', frame=1)
    rot = [0, 0, 0]
    rot[axis] = math.radians(360)
    ring.rotation_euler = rot
    ring.keyframe_insert('rotation_euler', frame=FRAME_END)
    for fc in ring.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    return ring

make_ring("RingA", NEON_MAGENTA, 3.2, 0)   # X축 회전
make_ring("RingB", NEON_CYAN, 3.8, 1)      # Y축 회전

# ---------- 은은한 보조 조명 ----------
bpy.ops.object.light_add(type='AREA', location=(0, -6, 5))
light = bpy.context.object
light.data.energy = 80
light.data.size = 8
light.rotation_euler = (math.radians(50), 0, 0)

# ---------- 카메라 (오빗 무브) ----------
bpy.ops.object.empty_add(location=(0, 0, 0))
pivot = bpy.context.object
pivot.name = "CamPivot"

bpy.ops.object.camera_add(location=(0, -9, 1.8))
cam = bpy.context.object
cam.data.lens = 40
cam.parent = pivot
track = cam.constraints.new(type='TRACK_TO')
track.target = txt
scene.camera = cam

# 피벗을 60도 회전시켜 카메라가 천천히 도는 느낌
pivot.rotation_euler = (0, 0, math.radians(-30))
pivot.keyframe_insert('rotation_euler', frame=1)
pivot.rotation_euler = (0, 0, math.radians(30))
pivot.keyframe_insert('rotation_euler', frame=FRAME_END)

# ---------- 컴포지터 글로우 (네온 느낌) ----------
scene.use_nodes = True
tree = scene.node_tree
for n in tree.nodes:
    tree.nodes.remove(n)
rl = tree.nodes.new('CompositorNodeRLayers')
glare = tree.nodes.new('CompositorNodeGlare')
glare.glare_type = 'FOG_GLOW'
glare.threshold = 0.9
glare.size = 8
comp = tree.nodes.new('CompositorNodeComposite')
tree.links.new(rl.outputs['Image'], glare.inputs['Image'])
tree.links.new(glare.outputs['Image'], comp.inputs['Image'])

# ---------- 렌더 설정 (Cycles CPU, MP4 출력) ----------
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100

out_dir = os.path.join(os.getcwd(), "output")
os.makedirs(out_dir, exist_ok=True)
scene.render.filepath = os.path.join(out_dir, "neon_intro.mp4")
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.ffmpeg.audio_codec = 'NONE'

# ---------- 렌더 실행 ----------
print(f">>> 렌더 시작: {FRAME_END} frames @ {FPS}fps")
bpy.ops.render.render(animation=True)
print(">>> 렌더 완료:", scene.render.filepath)
