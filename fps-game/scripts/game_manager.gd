extends Node3D

# Game state
var score: int = 0
var enemies_killed: int = 0
var game_over: bool = false
var paused: bool = false
var current_wave: int = 1
var enemies_in_wave: int = 0
var wave_active: bool = false

# Timers (replaces create_timer calls for performance)
var wave_spawn_timer: float = 0.0
var damage_boost_timer: float = 0.0
var damage_boost_amount: int = 0

# Pause menu
var pause_menu: Control

# References
@onready var player: CharacterBody3D = $Player
@onready var health_label: Label = $HUD/HealthLabel
@onready var ammo_label: Label = $HUD/AmmoLabel
@onready var score_label: Label = $HUD/ScoreLabel
@onready var enemies_container: Node3D = $Enemies

# UI elements we'll create
var wave_label: Label
var combo_label: Label
var armor_label: Label
var money_label: Label
var kill_feed: VBoxContainer

# Enemy spawning
@export var enemy_scene: PackedScene
var spawn_points: Array[Vector3] = []

func _ready() -> void:
	# Allow this node to process while paused
	process_mode = Node.PROCESS_MODE_ALWAYS

	# Connect player signals
	player.health_changed.connect(_on_player_health_changed)
	player.armor_changed.connect(_on_player_armor_changed)
	player.ammo_changed.connect(_on_player_ammo_changed)
	player.money_changed.connect(_on_player_money_changed)
	player.player_died.connect(_on_player_died)
	player.combo_changed.connect(_on_combo_changed)

	# Connect existing enemy signals
	for enemy in enemies_container.get_children():
		_setup_enemy(enemy)
		enemies_in_wave += 1

	# Setup spawn points around arena
	for i in range(8):
		var angle := i * TAU / 8.0
		spawn_points.append(Vector3(cos(angle) * 20.0, 1.0, sin(angle) * 20.0))

	# Try to load enemy scene for spawning
	if ResourceLoader.exists("res://scenes/enemy.tscn"):
		enemy_scene = load("res://scenes/enemy.tscn")

	# Setup additional HUD
	_setup_hud()

	# Initialize
	update_hud()
	wave_active = true
	_show_wave_announcement()

func _setup_hud() -> void:
	# Wave label (top center)
	wave_label = Label.new()
	wave_label.text = "WAVE 1"
	wave_label.add_theme_font_size_override("font_size", 28)
	wave_label.add_theme_color_override("font_color", Color(1, 0.8, 0.2))
	wave_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	wave_label.set_anchors_preset(Control.PRESET_CENTER_TOP)
	wave_label.position.y = 20
	$HUD.add_child(wave_label)

	# Combo label (center right)
	combo_label = Label.new()
	combo_label.text = ""
	combo_label.add_theme_font_size_override("font_size", 36)
	combo_label.add_theme_color_override("font_color", Color(1, 0.3, 0.3))
	combo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	combo_label.set_anchors_preset(Control.PRESET_CENTER_RIGHT)
	combo_label.position.x = -30
	$HUD.add_child(combo_label)

	# Armor label (below health)
	armor_label = Label.new()
	armor_label.text = "Armor: 0"
	armor_label.add_theme_font_size_override("font_size", 20)
	armor_label.add_theme_color_override("font_color", Color(0.3, 0.6, 1.0))
	armor_label.position = Vector2(20, 90)
	$HUD.add_child(armor_label)

	# Money label (below armor)
	money_label = Label.new()
	money_label.text = "$800"
	money_label.add_theme_font_size_override("font_size", 22)
	money_label.add_theme_color_override("font_color", Color(0.2, 0.9, 0.2))
	money_label.position = Vector2(20, 120)
	$HUD.add_child(money_label)

	# Kill feed (top right)
	kill_feed = VBoxContainer.new()
	kill_feed.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	kill_feed.position = Vector2(-250, 60)
	kill_feed.add_theme_constant_override("separation", 5)
	$HUD.add_child(kill_feed)

	# Controls hint (bottom left)
	var controls_label := Label.new()
	controls_label.text = "[ESC] Menu  [R] Reload  [TAB] Dash  [C] Crouch"
	controls_label.add_theme_font_size_override("font_size", 14)
	controls_label.add_theme_color_override("font_color", Color(1, 1, 1, 0.5))
	controls_label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	controls_label.position = Vector2(20, -40)
	$HUD.add_child(controls_label)

	# Create pause menu (hidden initially)
	_create_pause_menu()

func _create_pause_menu() -> void:
	pause_menu = Control.new()
	pause_menu.set_anchors_preset(Control.PRESET_FULL_RECT)
	pause_menu.visible = false
	$HUD.add_child(pause_menu)

	# Dark overlay
	var overlay := ColorRect.new()
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	overlay.color = Color(0, 0, 0, 0.7)
	pause_menu.add_child(overlay)

	# Menu container
	var vbox := VBoxContainer.new()
	vbox.set_anchors_preset(Control.PRESET_CENTER)
	vbox.alignment = BoxContainer.ALIGNMENT_CENTER
	pause_menu.add_child(vbox)

	# Title
	var title := Label.new()
	title.text = "PAUSED"
	title.add_theme_font_size_override("font_size", 64)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 30)
	vbox.add_child(spacer)

	# Resume button
	var resume_btn := Button.new()
	resume_btn.text = "RESUME"
	resume_btn.custom_minimum_size = Vector2(200, 50)
	resume_btn.pressed.connect(_on_resume_pressed)
	vbox.add_child(resume_btn)

	var spacer2 := Control.new()
	spacer2.custom_minimum_size = Vector2(0, 10)
	vbox.add_child(spacer2)

	# Restart button
	var restart_btn := Button.new()
	restart_btn.text = "RESTART"
	restart_btn.custom_minimum_size = Vector2(200, 50)
	restart_btn.pressed.connect(_on_restart_pressed)
	vbox.add_child(restart_btn)

	var spacer3 := Control.new()
	spacer3.custom_minimum_size = Vector2(0, 20)
	vbox.add_child(spacer3)

	# Stats
	var stats := Label.new()
	stats.text = "Press ESC to resume"
	stats.add_theme_font_size_override("font_size", 18)
	stats.add_theme_color_override("font_color", Color(1, 1, 1, 0.6))
	stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(stats)

func _toggle_pause() -> void:
	paused = !paused
	pause_menu.visible = paused
	get_tree().paused = paused

	if paused:
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	else:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _on_resume_pressed() -> void:
	_toggle_pause()

func _on_restart_pressed() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()

func _process(delta: float) -> void:
	if game_over:
		return

	# Process timers
	_process_timers(delta)

	# Check if wave is complete
	if wave_active and enemies_container.get_child_count() == 0:
		wave_active = false
		_start_next_wave()

func _process_timers(delta: float) -> void:
	# Wave spawn timer
	if wave_spawn_timer > 0:
		wave_spawn_timer -= delta
		if wave_spawn_timer <= 0:
			_spawn_wave()

	# Damage boost timer
	if damage_boost_timer > 0:
		damage_boost_timer -= delta
		if damage_boost_timer <= 0 and is_instance_valid(player):
			player.damage_per_shot = maxi(player.damage_per_shot - damage_boost_amount, 25)
			damage_boost_amount = 0

func _setup_enemy(enemy: Node3D) -> void:
	enemy.enemy_died.connect(_on_enemy_died)
	# Vary enemy stats based on wave
	if enemy.has_method("set_stats"):
		enemy.set_stats(current_wave)

func _start_next_wave() -> void:
	current_wave += 1
	print("Starting wave ", current_wave)
	wave_label.text = "WAVE %d" % current_wave
	_show_wave_announcement()

	# Heal player between waves
	player.health = mini(player.health + 25, player.max_health)
	player.emit_signal("health_changed", player.health)

	# Give ammo bonus
	player.reserve_ammo = mini(player.reserve_ammo + 30, player.max_reserve_ammo)
	player.emit_signal("ammo_changed", player.current_ammo, player.reserve_ammo)

	# Use timer variable instead of create_timer
	print("Setting up 2 second timer for wave spawn...")
	wave_spawn_timer = 2.0

func _spawn_wave() -> void:
	print("_spawn_wave called for wave ", current_wave)

	if enemy_scene == null:
		print("enemy_scene is null, trying to load...")
		# Try loading again
		if ResourceLoader.exists("res://scenes/enemy.tscn"):
			enemy_scene = load("res://scenes/enemy.tscn")
			print("Loaded enemy scene: ", enemy_scene)
		if enemy_scene == null:
			print("ERROR: Could not load enemy scene!")
			return

	var enemy_count := 4 + current_wave * 2  # More enemies each wave (gradual)
	enemy_count = mini(enemy_count, 20)  # Cap at 20
	print("Spawning ", enemy_count, " enemies for wave ", current_wave)

	# Spawn enemies immediately, not with delayed timers
	for i in range(enemy_count):
		_spawn_single_enemy()

	wave_active = true
	print("Wave ", current_wave, " active with ", enemies_container.get_child_count(), " enemies")

func _spawn_single_enemy() -> void:
	if enemy_scene == null:
		print("ERROR: enemy_scene is null in _spawn_single_enemy")
		return

	var enemy := enemy_scene.instantiate()

	# Random spawn from spawn points
	var spawn_pos: Vector3 = spawn_points[randi() % spawn_points.size()]
	# Add some randomness
	spawn_pos.x += randf_range(-5.0, 5.0)
	spawn_pos.z += randf_range(-5.0, 5.0)

	# Setup enemy before adding to tree
	_setup_enemy(enemy)

	# Scale difficulty with waves
	if enemy.has_node("Body"):
		var scale_mult := 1.0 + (current_wave - 1) * 0.1
		enemy.scale = Vector3.ONE * minf(scale_mult, 1.5)

	# Add to scene tree FIRST, then set position
	enemies_container.add_child(enemy)
	enemy.global_position = spawn_pos

	# Spawn effect
	_spawn_effect(spawn_pos)
	print("Spawned enemy at ", spawn_pos)

func _spawn_effect(pos: Vector3) -> void:
	var effect := GPUParticles3D.new()
	effect.emitting = true
	effect.one_shot = true
	effect.amount = 20
	effect.lifetime = 0.5
	effect.explosiveness = 1.0

	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	mat.emission_sphere_radius = 0.5
	mat.direction = Vector3(0, 1, 0)
	mat.spread = 180.0
	mat.initial_velocity_min = 3.0
	mat.initial_velocity_max = 6.0
	mat.gravity = Vector3(0, -5, 0)
	mat.color = Color(1, 0.3, 0.3)
	effect.process_material = mat

	var mesh := SphereMesh.new()
	mesh.radius = 0.05
	mesh.height = 0.1
	effect.draw_pass_1 = mesh

	add_child(effect)
	effect.global_position = pos

	# Use tween callback instead of create_timer for cleanup
	var cleanup_tween := create_tween()
	cleanup_tween.tween_interval(1.0)
	cleanup_tween.tween_callback(effect.queue_free)

func _show_wave_announcement() -> void:
	var announce := Label.new()
	announce.text = "WAVE %d" % current_wave
	announce.add_theme_font_size_override("font_size", 72)
	announce.add_theme_color_override("font_color", Color(1, 0.8, 0.2))
	announce.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	announce.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	announce.set_anchors_preset(Control.PRESET_CENTER)
	$HUD.add_child(announce)

	var tween := create_tween()
	tween.tween_property(announce, "scale", Vector2(1.5, 1.5), 0.3)
	tween.tween_property(announce, "modulate:a", 0.0, 1.0)
	tween.tween_callback(announce.queue_free)

func update_hud() -> void:
	health_label.text = "Health: %d" % player.health
	ammo_label.text = "Ammo: %d / %d" % [player.current_ammo, player.reserve_ammo]
	score_label.text = "Score: %d" % score

func _on_player_health_changed(new_health: int) -> void:
	health_label.text = "Health: %d" % new_health

	# Health color feedback
	if new_health <= 25:
		health_label.add_theme_color_override("font_color", Color.RED)
	elif new_health <= 50:
		health_label.add_theme_color_override("font_color", Color.YELLOW)
	else:
		health_label.remove_theme_color_override("font_color")

func _on_player_armor_changed(new_armor: int) -> void:
	armor_label.text = "Armor: %d" % new_armor

func _on_player_money_changed(new_money: int) -> void:
	money_label.text = "$%d" % new_money

func _on_player_ammo_changed(current: int, reserve: int) -> void:
	ammo_label.text = "Ammo: %d / %d" % [current, reserve]

	if current <= 5:
		ammo_label.add_theme_color_override("font_color", Color.ORANGE)
	else:
		ammo_label.remove_theme_color_override("font_color")

func _on_combo_changed(combo: int) -> void:
	if combo >= 2:
		combo_label.text = "%dx COMBO!" % combo
		# Pulse effect
		var tween := create_tween()
		tween.tween_property(combo_label, "scale", Vector2(1.3, 1.3), 0.1)
		tween.tween_property(combo_label, "scale", Vector2.ONE, 0.1)

		# Color based on combo
		if combo >= 10:
			combo_label.add_theme_color_override("font_color", Color(1, 0, 1))  # Purple
		elif combo >= 5:
			combo_label.add_theme_color_override("font_color", Color(1, 0.5, 0))  # Orange
		else:
			combo_label.add_theme_color_override("font_color", Color(1, 0.3, 0.3))  # Red
	else:
		combo_label.text = ""

func _on_enemy_died(enemy: Node3D) -> void:
	enemies_killed += 1

	# Base score + wave bonus + combo multiplier
	var base_score: int = 100
	var wave_bonus: int = current_wave * 25
	var combo_mult: float = 1.0 + float(player.kill_combo) * 0.1
	score += int(float(base_score + wave_bonus) * combo_mult)

	# Give money for kill ($300 base + wave bonus)
	var kill_reward := 300 + current_wave * 50
	player.add_money(kill_reward)

	# Update combo
	player.add_combo()

	# Screen shake
	player.add_screen_shake(0.15)

	# Add to kill feed
	_add_kill_feed("Enemy eliminated +$%d" % kill_reward)

	score_label.text = "Score: %d" % score

	# Random power-up drop (20% chance)
	if randf() < 0.2:
		_spawn_powerup(enemy.global_position)

func _add_kill_feed(text: String) -> void:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_color_override("font_color", Color(1, 0.3, 0.3))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	kill_feed.add_child(label)

	# Fade out and remove
	var tween := create_tween()
	tween.tween_interval(2.0)
	tween.tween_property(label, "modulate:a", 0.0, 0.5)
	tween.tween_callback(label.queue_free)

	# Limit kill feed size
	if kill_feed.get_child_count() > 5:
		kill_feed.get_child(0).queue_free()

func _spawn_powerup(pos: Vector3) -> void:
	var powerup := Area3D.new()
	powerup.collision_layer = 0
	powerup.collision_mask = 2  # Player layer

	var col := CollisionShape3D.new()
	var shape := SphereShape3D.new()
	shape.radius = 0.8
	col.shape = shape
	powerup.add_child(col)

	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(0.5, 0.5, 0.5)
	mesh_instance.mesh = mesh

	# Random powerup type
	var powerup_type := randi() % 4
	var mat := StandardMaterial3D.new()
	mat.emission_enabled = true
	mat.emission_energy_multiplier = 2.0

	match powerup_type:
		0:  # Health
			mat.albedo_color = Color(0, 1, 0)
			mat.emission = Color(0, 1, 0)
			powerup.set_meta("type", "health")
		1:  # Ammo
			mat.albedo_color = Color(1, 1, 0)
			mat.emission = Color(1, 1, 0)
			powerup.set_meta("type", "ammo")
		2:  # Damage boost
			mat.albedo_color = Color(1, 0, 0)
			mat.emission = Color(1, 0, 0)
			powerup.set_meta("type", "damage")
		3:  # Armor
			mat.albedo_color = Color(0.3, 0.5, 1.0)
			mat.emission = Color(0.3, 0.5, 1.0)
			powerup.set_meta("type", "armor")

	mesh_instance.set_surface_override_material(0, mat)
	powerup.add_child(mesh_instance)

	add_child(powerup)
	powerup.global_position = pos + Vector3(0, 0.5, 0)

	# Floating animation
	var tween := create_tween().set_loops()
	tween.tween_property(powerup, "position:y", pos.y + 1.0, 0.5)
	tween.tween_property(powerup, "position:y", pos.y + 0.5, 0.5)

	# Rotation
	var rot_tween := create_tween().set_loops()
	rot_tween.tween_property(mesh_instance, "rotation:y", TAU, 2.0)

	# Pickup detection
	powerup.body_entered.connect(func(body):
		if body == player:
			_pickup_powerup(powerup)
	)

	# Despawn after 10 seconds using tween instead of create_timer
	var despawn_tween := create_tween()
	despawn_tween.tween_interval(10.0)
	despawn_tween.tween_callback(func():
		if is_instance_valid(powerup):
			powerup.queue_free()
	)

func _pickup_powerup(powerup: Area3D) -> void:
	# Null safety check
	if not is_instance_valid(powerup):
		return

	var type: String = powerup.get_meta("type", "")

	match type:
		"health":
			player.health = mini(player.health + 30, player.max_health)
			player.emit_signal("health_changed", player.health)
			_show_pickup_text("+30 HP", Color.GREEN)
		"ammo":
			player.reserve_ammo = mini(player.reserve_ammo + 30, player.max_reserve_ammo)
			player.emit_signal("ammo_changed", player.current_ammo, player.reserve_ammo)
			_show_pickup_text("+30 AMMO", Color.YELLOW)
		"damage":
			player.damage_per_shot += 10
			_show_pickup_text("DAMAGE UP!", Color.RED)
			# Use timer variable instead of create_timer
			damage_boost_amount = 10
			damage_boost_timer = 10.0
		"armor":
			player.armor = mini(player.armor + 50, 100)
			player.emit_signal("armor_changed", player.armor)
			_show_pickup_text("+50 ARMOR", Color(0.3, 0.6, 1.0))

	powerup.queue_free()

func _show_pickup_text(text: String, color: Color) -> void:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", 28)
	label.add_theme_color_override("font_color", color)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.set_anchors_preset(Control.PRESET_CENTER)
	label.position.y = 50
	$HUD.add_child(label)

	var tween := create_tween()
	tween.tween_property(label, "position:y", 0, 0.5)
	tween.parallel().tween_property(label, "modulate:a", 0.0, 0.8)
	tween.tween_callback(label.queue_free)

func _on_player_died() -> void:
	game_over = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

	var panel := Panel.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.modulate = Color(0, 0, 0, 0.7)
	$HUD.add_child(panel)

	var game_over_label := Label.new()
	game_over_label.text = "GAME OVER\n\nWave: %d\nScore: %d\nKills: %d\n\nPress R to Restart" % [current_wave, score, enemies_killed]
	game_over_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	game_over_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	game_over_label.add_theme_font_size_override("font_size", 48)
	game_over_label.set_anchors_preset(Control.PRESET_CENTER)
	$HUD.add_child(game_over_label)

func _input(event: InputEvent) -> void:
	# Pause toggle
	if event.is_action_pressed("ui_cancel") and not game_over:
		_toggle_pause()
		get_viewport().set_input_as_handled()
		return

	# Restart from game over
	if game_over and event.is_action_pressed("reload"):
		get_tree().reload_current_scene()
