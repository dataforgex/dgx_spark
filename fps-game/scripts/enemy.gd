extends CharacterBody3D

# Stats
@export var max_health: int = 100
@export var move_speed: float = 4.0
@export var attack_damage: int = 10
@export var attack_range: float = 2.5
@export var attack_cooldown: float = 1.0
@export var detection_range: float = 25.0

# Behavior variation
var strafe_timer: float = 0.0
var strafe_direction: float = 1.0
var is_charging: bool = false
var base_speed: float = 4.0

# State
var health: int = 100
var can_attack: bool = true
var is_dead: bool = false
var target: Node3D = null
var gravity: float = 20.0

# Cooldown timers (replaces create_timer calls for performance)
var attack_cooldown_timer: float = 0.0
var charge_duration_timer: float = 0.0
var body_flash_timer: float = 0.0
var head_flash_timer: float = 0.0
var death_cleanup_timer: float = 0.0
var original_body_color: Color = Color.RED
var original_head_color: Color = Color.RED

# Node references
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D
@onready var body_mesh: MeshInstance3D = $Body
@onready var head_mesh: MeshInstance3D = $Head

# Signals
signal enemy_died(enemy: Node3D)

func _ready() -> void:
	health = max_health
	base_speed = move_speed

	# Make materials unique so dying enemies don't affect others
	var body_mat = body_mesh.get_surface_override_material(0)
	if body_mat:
		body_mesh.set_surface_override_material(0, body_mat.duplicate())
		original_body_color = body_mat.albedo_color
	var head_mat = head_mesh.get_surface_override_material(0)
	if head_mat:
		head_mesh.set_surface_override_material(0, head_mat.duplicate())
		original_head_color = head_mat.albedo_color

	# Randomize behavior slightly
	move_speed = randf_range(base_speed * 0.8, base_speed * 1.3)
	strafe_direction = 1.0 if randf() > 0.5 else -1.0

	# Find player
	await get_tree().process_frame
	var players := get_tree().get_nodes_in_group("player")
	if players.size() > 0:
		target = players[0]

func set_stats(wave: int) -> void:
	# Scale stats with wave (gradual increase)
	max_health = 80 + wave * 10
	health = max_health
	move_speed = 3.5 + wave * 0.15
	base_speed = move_speed
	attack_damage = 8 + wave * 1
	attack_cooldown = maxf(0.7, 1.2 - wave * 0.03)

func _physics_process(delta: float) -> void:
	if is_dead:
		# Handle death cleanup timer
		if death_cleanup_timer > 0:
			death_cleanup_timer -= delta
			if death_cleanup_timer <= 0:
				queue_free()
		return

	# Process all cooldown timers
	_process_timers(delta)

	# Apply gravity
	if not is_on_floor():
		velocity.y -= gravity * delta

	if target == null or not is_instance_valid(target):
		return

	# Process AI behavior
	_process_behavior(delta)

func _process_timers(delta: float) -> void:
	# Attack cooldown
	if attack_cooldown_timer > 0:
		attack_cooldown_timer -= delta
		if attack_cooldown_timer <= 0:
			can_attack = true

	# Charge duration
	if charge_duration_timer > 0:
		charge_duration_timer -= delta
		if charge_duration_timer <= 0:
			is_charging = false
			if is_instance_valid(body_mesh):
				var mat: StandardMaterial3D = body_mesh.get_surface_override_material(0)
				if mat:
					mat.emission_enabled = false

	# Body flash timer
	if body_flash_timer > 0:
		body_flash_timer -= delta
		if body_flash_timer <= 0 and is_instance_valid(body_mesh):
			var body_mat: StandardMaterial3D = body_mesh.get_surface_override_material(0)
			if body_mat:
				body_mat.albedo_color = original_body_color
				body_mat.emission_enabled = false

	# Head flash timer
	if head_flash_timer > 0:
		head_flash_timer -= delta
		if head_flash_timer <= 0 and is_instance_valid(head_mesh):
			var head_mat: StandardMaterial3D = head_mesh.get_surface_override_material(0)
			if head_mat:
				head_mat.albedo_color = original_head_color
				head_mat.emission_enabled = false

func _process_behavior(delta: float) -> void:
	var distance_to_target := global_position.distance_to(target.global_position)

	# Look at player
	var look_target := target.global_position
	look_target.y = global_position.y
	look_at(look_target, Vector3.UP)

	# Strafe timer - change direction periodically
	strafe_timer -= delta
	if strafe_timer <= 0:
		strafe_timer = randf_range(1.0, 3.0)
		strafe_direction *= -1.0
		# Random chance to charge (only if not already charging)
		if randf() < 0.3 and distance_to_target > 8.0 and not is_charging:
			_start_charge()

	# Chase or attack
	if distance_to_target <= attack_range:
		# Stop and attack
		velocity.x = 0
		velocity.z = 0
		is_charging = false
		if can_attack:
			attack()
	elif distance_to_target <= detection_range:
		# Get direction to player
		var to_player := (target.global_position - global_position).normalized()
		to_player.y = 0

		if is_charging:
			# Charge straight at player fast
			velocity.x = to_player.x * move_speed * 2.0
			velocity.z = to_player.z * move_speed * 2.0
		else:
			# Normal chase with strafing at medium range
			var current_speed := move_speed

			if distance_to_target < 10.0 and distance_to_target > attack_range + 1.0:
				# Add strafing when close but not attacking
				var strafe_vec := Vector3(-to_player.z, 0, to_player.x) * strafe_direction
				var move_dir := (to_player * 0.7 + strafe_vec * 0.3).normalized()
				velocity.x = move_dir.x * current_speed
				velocity.z = move_dir.z * current_speed
			else:
				# Direct chase using navigation
				nav_agent.target_position = target.global_position
				if not nav_agent.is_navigation_finished():
					var next_pos := nav_agent.get_next_path_position()
					var direction := (next_pos - global_position).normalized()
					direction.y = 0
					velocity.x = direction.x * current_speed
					velocity.z = direction.z * current_speed
	else:
		# Idle - slow down
		velocity.x = move_toward(velocity.x, 0, move_speed * 0.5)
		velocity.z = move_toward(velocity.z, 0, move_speed * 0.5)

	move_and_slide()

func _start_charge() -> void:
	is_charging = true
	# Visual feedback - enemy glows red
	var body_mat: StandardMaterial3D = body_mesh.get_surface_override_material(0)
	if body_mat:
		body_mat.emission_enabled = true
		body_mat.emission = Color(1, 0, 0)
		body_mat.emission_energy_multiplier = 1.5

	# Use timer variable instead of create_timer
	charge_duration_timer = 1.5

func attack() -> void:
	can_attack = false

	# Attack animation - lunge forward
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3(1.2, 0.8, 1.2), 0.1)
	tween.tween_property(self, "scale", Vector3.ONE, 0.2)

	# Deal damage (with null safety)
	if target and is_instance_valid(target) and target.has_method("take_damage"):
		target.take_damage(attack_damage)

	# Use timer variable instead of create_timer
	attack_cooldown_timer = attack_cooldown

func take_damage(amount: int, is_headshot: bool = false) -> void:
	if is_dead:
		return

	health -= amount

	# Hit flash effect using unified flash function
	if is_headshot:
		_flash(Color.YELLOW, 0.15, true)  # Headshot flash with emission
	else:
		_flash(Color.WHITE, 0.1, false)  # Normal hit flash

	if health <= 0:
		die()

# Unified flash function to reduce code duplication
func _flash(flash_color: Color, duration: float, with_emission: bool) -> void:
	var body_mat: StandardMaterial3D = body_mesh.get_surface_override_material(0) if is_instance_valid(body_mesh) else null
	var head_mat: StandardMaterial3D = head_mesh.get_surface_override_material(0) if is_instance_valid(head_mesh) else null

	if body_mat:
		body_mat.albedo_color = flash_color
		if with_emission:
			body_mat.emission_enabled = true
			body_mat.emission = flash_color
			body_mat.emission_energy_multiplier = 2.0

	if head_mat:
		head_mat.albedo_color = flash_color
		if with_emission:
			head_mat.emission_enabled = true
			head_mat.emission = flash_color
			head_mat.emission_energy_multiplier = 3.0

	# Use timer variables instead of create_timer
	body_flash_timer = duration
	head_flash_timer = duration

func die() -> void:
	is_dead = true
	emit_signal("enemy_died", self)

	# Death animation - shrink and fade materials
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(self, "scale:y", 0.1, 0.3)

	# Fade out materials (with null safety)
	var body_mat: StandardMaterial3D = body_mesh.get_surface_override_material(0) if is_instance_valid(body_mesh) else null
	var head_mat: StandardMaterial3D = head_mesh.get_surface_override_material(0) if is_instance_valid(head_mesh) else null
	if body_mat:
		body_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		tween.tween_property(body_mat, "albedo_color:a", 0.0, 0.5)
	if head_mat:
		head_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		tween.tween_property(head_mat, "albedo_color:a", 0.0, 0.5)

	# Disable collision
	collision_layer = 0
	collision_mask = 0

	# Use timer variable instead of create_timer for cleanup
	death_cleanup_timer = 0.5
