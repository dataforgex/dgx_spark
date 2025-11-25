extends CharacterBody3D

# Movement settings
@export var move_speed: float = 8.0
@export var sprint_speed: float = 14.0
@export var jump_velocity: float = 6.0
@export var mouse_sensitivity: float = 0.002
@export var gravity: float = 25.0
@export var dash_speed: float = 25.0
@export var dash_cooldown: float = 1.5

# Combat settings
@export var max_health: int = 100
@export var damage_per_shot: int = 25
@export var headshot_multiplier: float = 3.0
@export var fire_rate: float = 0.1
@export var max_ammo: int = 30
@export var max_reserve_ammo: int = 90
@export var reload_time: float = 1.5

# State
var health: int = 100
var armor: int = 0
var current_ammo: int = 30
var reserve_ammo: int = 90
var can_shoot: bool = true
var is_reloading: bool = false
var can_dash: bool = true
var is_dashing: bool = false
var is_crouching: bool = false
var kill_combo: int = 0
var combo_timer: float = 0.0
var screen_shake: float = 0.0
var money: int = 800

# Cooldown timers (replaces create_timer calls for performance)
var fire_rate_timer: float = 0.0
var dash_duration_timer: float = 0.0
var dash_cooldown_timer: float = 0.0
var reload_timer: float = 0.0
var muzzle_flash_timer: float = 0.0
var speed_boost_timer: float = 0.0
var original_move_speed: float = 8.0

# Footsteps
var footstep_timer: float = 0.0
var footstep_sound: AudioStreamPlayer

# Node references
@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var raycast: RayCast3D = $Head/Camera3D/RayCast3D
@onready var gun_pivot: Node3D = $Head/Camera3D/GunPivot
@onready var muzzle_flash: OmniLight3D = $Head/Camera3D/GunPivot/MuzzleFlash

# Audio
var shoot_sound: AudioStreamPlayer
var reload_sound: AudioStreamPlayer
var headshot_sound: AudioStreamPlayer

# Signals
signal health_changed(new_health: int)
signal armor_changed(new_armor: int)
signal ammo_changed(current: int, reserve: int)
signal money_changed(new_money: int)
signal player_died
signal combo_changed(combo: int)
signal enemy_killed

func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	health = max_health
	current_ammo = max_ammo
	reserve_ammo = max_reserve_ammo
	original_move_speed = move_speed
	_setup_audio()

func _setup_audio() -> void:
	# Create shoot sound
	shoot_sound = AudioStreamPlayer.new()
	shoot_sound.volume_db = -5
	add_child(shoot_sound)
	shoot_sound.stream = _generate_gunshot_sound()

	# Create reload sound
	reload_sound = AudioStreamPlayer.new()
	reload_sound.volume_db = -8
	add_child(reload_sound)
	reload_sound.stream = _generate_reload_sound()

	# Create headshot sound
	headshot_sound = AudioStreamPlayer.new()
	headshot_sound.volume_db = 0
	add_child(headshot_sound)
	headshot_sound.stream = _generate_headshot_sound()

	# Create footstep sound
	footstep_sound = AudioStreamPlayer.new()
	footstep_sound.volume_db = -12
	add_child(footstep_sound)
	footstep_sound.stream = _generate_footstep_sound()

# Unified audio generation helper to reduce code duplication
func _generate_audio(duration: float, generator: Callable) -> AudioStreamWAV:
	var sample_rate := 22050
	var samples := int(sample_rate * duration)
	var audio := AudioStreamWAV.new()
	audio.format = AudioStreamWAV.FORMAT_8_BITS
	audio.mix_rate = sample_rate

	var data := PackedByteArray()
	data.resize(samples)

	for i in range(samples):
		var t := float(i) / sample_rate
		var sample: float = generator.call(t)
		data[i] = int((clampf(sample, -1.0, 1.0) + 1.0) * 127.5)

	audio.data = data
	return audio

func _generate_gunshot_sound() -> AudioStreamWAV:
	return _generate_audio(0.15, func(t: float) -> float:
		var envelope := exp(-t * 30.0)
		var noise := (randf() * 2.0 - 1.0) * envelope
		var low_freq := sin(t * 150.0 * TAU) * envelope * 0.5
		return (noise + low_freq) * 0.5
	)

func _generate_reload_sound() -> AudioStreamWAV:
	return _generate_audio(0.3, func(t: float) -> float:
		var click1 := 0.0
		var click2 := 0.0
		if t < 0.05:
			click1 = sin(t * 800.0 * TAU) * exp(-t * 40.0)
		if t > 0.15 and t < 0.25:
			var t2 := t - 0.15
			click2 = sin(t2 * 600.0 * TAU) * exp(-t2 * 30.0)
		return (click1 + click2) * 0.8
	)

func _generate_headshot_sound() -> AudioStreamWAV:
	return _generate_audio(0.25, func(t: float) -> float:
		var envelope := exp(-t * 15.0)
		var ping := sin(t * 1200.0 * TAU) * envelope
		var ping2 := sin(t * 1800.0 * TAU) * envelope * 0.5
		return (ping + ping2) * 0.6
	)

func _generate_footstep_sound() -> AudioStreamWAV:
	return _generate_audio(0.1, func(t: float) -> float:
		var envelope := exp(-t * 50.0)
		var thud := sin(t * 80.0 * TAU) * envelope
		var noise := (randf() * 2.0 - 1.0) * envelope * 0.3
		return (thud + noise) * 0.5
	)

func _input(event: InputEvent) -> void:
	# Mouse look
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		head.rotate_x(-event.relative.y * mouse_sensitivity)
		head.rotation.x = clamp(head.rotation.x, -PI/2, PI/2)

	# Toggle mouse capture
	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _physics_process(delta: float) -> void:
	# Process all cooldown timers (replaces create_timer calls)
	_process_timers(delta)

	# Combo timer
	if combo_timer > 0:
		combo_timer -= delta
		if combo_timer <= 0:
			kill_combo = 0
			emit_signal("combo_changed", 0)

	# Screen shake decay
	if screen_shake > 0:
		screen_shake = lerp(screen_shake, 0.0, 10.0 * delta)
		camera.rotation.x += randf_range(-screen_shake, screen_shake) * 0.1
		camera.rotation.z = randf_range(-screen_shake, screen_shake) * 0.05

	# Apply gravity
	if not is_on_floor() and not is_dashing:
		velocity.y -= gravity * delta

	# Jump
	if Input.is_action_just_pressed("jump") and is_on_floor() and not is_crouching:
		velocity.y = jump_velocity

	# Crouch (C or Ctrl)
	var wants_crouch := Input.is_action_pressed("ui_copy") or Input.is_key_pressed(KEY_C)
	if wants_crouch and not is_crouching:
		is_crouching = true
		head.position.y = 1.0  # Lower camera
	elif not wants_crouch and is_crouching:
		is_crouching = false
		head.position.y = 1.6  # Normal height

	# Dash (Shift key)
	if Input.is_action_just_pressed("ui_focus_next") and can_dash and not is_crouching:
		dash()

	# Process movement, shooting, and other input
	_process_movement(delta)

func _process_timers(delta: float) -> void:
	# Fire rate cooldown
	if fire_rate_timer > 0:
		fire_rate_timer -= delta
		if fire_rate_timer <= 0:
			can_shoot = true

	# Dash duration
	if dash_duration_timer > 0:
		dash_duration_timer -= delta
		if dash_duration_timer <= 0:
			is_dashing = false

	# Dash cooldown
	if dash_cooldown_timer > 0:
		dash_cooldown_timer -= delta
		if dash_cooldown_timer <= 0:
			can_dash = true

	# Reload timer
	if reload_timer > 0:
		reload_timer -= delta
		if reload_timer <= 0:
			finish_reload()

	# Muzzle flash
	if muzzle_flash_timer > 0:
		muzzle_flash_timer -= delta
		if muzzle_flash_timer <= 0:
			muzzle_flash.visible = false

	# Speed boost from combo
	if speed_boost_timer > 0:
		speed_boost_timer -= delta
		if speed_boost_timer <= 0:
			move_speed = original_move_speed

func _process_movement(delta: float) -> void:
	# Get input direction
	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

	# Apply movement (unless dashing)
	if not is_dashing:
		var speed := move_speed
		if is_crouching:
			speed *= 0.4  # Slower when crouching
		if direction:
			velocity.x = direction.x * speed
			velocity.z = direction.z * speed
		else:
			velocity.x = move_toward(velocity.x, 0, speed)
			velocity.z = move_toward(velocity.z, 0, speed)

	move_and_slide()

	# Footsteps
	if is_on_floor() and velocity.length() > 1.0 and not is_crouching:
		footstep_timer -= delta
		if footstep_timer <= 0:
			footstep_sound.pitch_scale = randf_range(0.9, 1.1)
			footstep_sound.play()
			footstep_timer = 0.35

	# Shooting
	if Input.is_action_pressed("shoot") and can_shoot and not is_reloading:
		shoot()

	# Reload
	if Input.is_action_just_pressed("reload") and not is_reloading:
		reload()

	# Gun bob animation
	var bob_amount := 0.0
	if is_on_floor() and velocity.length() > 0.5:
		bob_amount = sin(Time.get_ticks_msec() * 0.015) * 0.03
	gun_pivot.position.y = lerp(gun_pivot.position.y, -0.15 + bob_amount, 0.15)

func dash() -> void:
	can_dash = false
	is_dashing = true

	# Dash in movement direction or forward
	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var dash_dir: Vector3
	if input_dir.length() > 0.1:
		dash_dir = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	else:
		dash_dir = -transform.basis.z

	velocity = dash_dir * dash_speed
	velocity.y = 2.0  # Slight lift

	# FOV effect
	var tween := create_tween()
	tween.tween_property(camera, "fov", 100.0, 0.1)
	tween.tween_property(camera, "fov", 90.0, 0.2)

	# Use timer variables instead of create_timer
	dash_duration_timer = 0.2
	dash_cooldown_timer = dash_cooldown

func add_combo() -> void:
	kill_combo += 1
	combo_timer = 3.0  # 3 seconds to maintain combo
	emit_signal("combo_changed", kill_combo)

	# Bonus effects for high combos
	if kill_combo >= 3:
		screen_shake = 0.3
	if kill_combo >= 5:
		# Speed boost using timer variable
		move_speed = original_move_speed + 2.0
		speed_boost_timer = 2.0

func add_screen_shake(amount: float) -> void:
	screen_shake = max(screen_shake, amount)

func shoot() -> void:
	if current_ammo <= 0:
		# Auto reload when empty
		reload()
		return

	can_shoot = false
	current_ammo -= 1
	emit_signal("ammo_changed", current_ammo, reserve_ammo)

	# Play shoot sound
	shoot_sound.play()

	# Muzzle flash using timer variable
	muzzle_flash.visible = true
	muzzle_flash_timer = 0.05

	# Gun recoil animation
	var tween := create_tween()
	tween.tween_property(gun_pivot, "position:z", -0.35, 0.03)
	tween.tween_property(gun_pivot, "position:z", -0.4, 0.1)

	# Raycast hit detection
	if raycast.is_colliding():
		var collider := raycast.get_collider()
		# Null safety check
		if collider == null:
			fire_rate_timer = fire_rate
			return

		var hit_point := raycast.get_collision_point()

		# Spawn hit effect and bullet tracer
		spawn_hit_effect(hit_point)
		_spawn_bullet_tracer(gun_pivot.global_position, hit_point)

		# Damage enemy with headshot detection (with validity check)
		if is_instance_valid(collider) and collider.is_in_group("enemies"):
			var is_headshot := _check_headshot(collider, hit_point)
			var final_damage := damage_per_shot
			if is_headshot:
				final_damage = int(damage_per_shot * headshot_multiplier)
				headshot_sound.play()
				_show_headshot_indicator()
			if collider.has_method("take_damage"):
				collider.take_damage(final_damage, is_headshot)

	# Fire rate cooldown using timer variable
	fire_rate_timer = fire_rate

func _check_headshot(enemy: Node3D, hit_point: Vector3) -> bool:
	# Null safety check
	if not is_instance_valid(enemy):
		return false
	# Try to get the actual head node safely
	var head_node = enemy.get_node_or_null("Head")
	if head_node != null:
		var head_pos: Vector3 = head_node.global_position
		var dist: float = hit_point.distance_to(head_pos)
		return dist < 0.6  # Head radius + margin
	# Fallback
	return hit_point.y > enemy.global_position.y + 1.5

func _show_headshot_indicator() -> void:
	# Find or create headshot label in HUD
	var hud := get_tree().get_first_node_in_group("hud")
	if hud == null:
		hud = get_node_or_null("/root/Main/HUD")
	if hud == null:
		return

	var label := Label.new()
	label.text = "HEADSHOT!"
	label.add_theme_font_size_override("font_size", 32)
	label.add_theme_color_override("font_color", Color(1, 0.2, 0.2))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.set_anchors_preset(Control.PRESET_CENTER)
	label.position.y = -100
	hud.add_child(label)

	# Animate and remove
	var tween := create_tween()
	tween.tween_property(label, "modulate:a", 0.0, 0.8)
	tween.tween_callback(label.queue_free)

func reload() -> void:
	if reserve_ammo <= 0 or current_ammo >= max_ammo or is_reloading:
		return

	is_reloading = true

	# Play reload sound
	reload_sound.play()

	# Reload animation
	var tween := create_tween()
	tween.tween_property(gun_pivot, "rotation:x", 0.5, reload_time * 0.3)
	tween.tween_property(gun_pivot, "rotation:x", 0.0, reload_time * 0.7)

	# Use timer variable instead of create_timer
	reload_timer = reload_time

func finish_reload() -> void:
	var ammo_needed: int = max_ammo - current_ammo
	var ammo_to_add: int = mini(ammo_needed, reserve_ammo)

	current_ammo += ammo_to_add
	reserve_ammo -= ammo_to_add

	is_reloading = false
	emit_signal("ammo_changed", current_ammo, reserve_ammo)

func spawn_hit_effect(pos: Vector3) -> void:
	# Create a simple particle effect at hit location
	var effect := GPUParticles3D.new()
	effect.emitting = true
	effect.one_shot = true
	effect.explosiveness = 1.0
	effect.amount = 8
	effect.lifetime = 0.3

	var material := ParticleProcessMaterial.new()
	material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	material.emission_sphere_radius = 0.1
	material.direction = Vector3(0, 1, 0)
	material.spread = 45.0
	material.initial_velocity_min = 2.0
	material.initial_velocity_max = 5.0
	material.gravity = Vector3(0, -10, 0)
	material.scale_min = 0.05
	material.scale_max = 0.1
	material.color = Color(1, 0.8, 0.2)
	effect.process_material = material

	var mesh := SphereMesh.new()
	mesh.radius = 0.02
	mesh.height = 0.04
	effect.draw_pass_1 = mesh

	get_tree().root.add_child(effect)
	effect.global_position = pos

	# Auto cleanup using tween instead of create_timer
	var cleanup_tween := create_tween()
	cleanup_tween.tween_interval(1.0)
	cleanup_tween.tween_callback(effect.queue_free)

func take_damage(amount: int) -> void:
	var actual_damage := amount

	# Armor absorbs 50% of damage
	if armor > 0:
		var armor_absorb := int(amount * 0.5)
		armor_absorb = mini(armor_absorb, armor)
		armor -= armor_absorb
		actual_damage = amount - armor_absorb
		emit_signal("armor_changed", armor)

	health -= actual_damage
	health = max(health, 0)
	emit_signal("health_changed", health)

	# Screen shake effect
	screen_shake = 0.3
	var tween := create_tween()
	tween.tween_property(camera, "rotation:z", 0.05, 0.05)
	tween.tween_property(camera, "rotation:z", -0.05, 0.05)
	tween.tween_property(camera, "rotation:z", 0.0, 0.05)

	if health <= 0:
		die()

func add_money(amount: int) -> void:
	money += amount
	money = mini(money, 16000)  # CS max money
	emit_signal("money_changed", money)

func _spawn_bullet_tracer(from: Vector3, to: Vector3) -> void:
	var tracer := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.01
	mesh.bottom_radius = 0.01
	mesh.height = from.distance_to(to)
	tracer.mesh = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1, 0.9, 0.5, 0.8)
	mat.emission_enabled = true
	mat.emission = Color(1, 0.8, 0.3)
	mat.emission_energy_multiplier = 3.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	tracer.set_surface_override_material(0, mat)

	get_tree().root.add_child(tracer)
	tracer.global_position = (from + to) / 2.0
	tracer.look_at(to, Vector3.UP)
	tracer.rotate_object_local(Vector3(1, 0, 0), PI / 2)

	# Fade out
	var tween := create_tween()
	tween.tween_property(mat, "albedo_color:a", 0.0, 0.1)
	tween.tween_callback(tracer.queue_free)

func die() -> void:
	emit_signal("player_died")
	# Could add death animation, respawn logic, etc.
