import krpc
import time
import math
import csv
import datetime

conn = krpc.connect(name='Kerbal-M')
vessel = conn.space_center.active_vessel
# Целевые параметры орбиты
target_orbit = 102_000

altitude_start = 1000 # Начало гравитационного разворота
target_altitude = 45000 # Конец гравитационного разворота

#Потоки данных телеметрии
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')
ut = conn.add_stream(getattr, conn.space_center, 'ut')
speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), 'speed')
mass = conn.add_stream(getattr, vessel, 'mass')

telemetry_file = f'telemetry_{datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.csv'
telemetry_csv = open(telemetry_file, 'w', newline='', encoding='utf-8')
telemetry_writer = csv.writer(telemetry_csv)
telemetry_writer.writerow(['Время', 'Высота', 'Скорость', 'Масса', 'Доступный delta_v'])

stage_6 = vessel.resources_in_decouple_stage(stage=6, cumulative=False)
liquid_fuel_6 = conn.add_stream(stage_6.amount, 'LiquidFuel')
stage_5 = vessel.resources_in_decouple_stage(stage=5, cumulative=False)
liquid_fuel_5 = conn.add_stream(stage_5.amount, 'LiquidFuel')
stage_4 = vessel.resources_in_decouple_stage(stage=4, cumulative=False)
liquid_fuel_4 = conn.add_stream(stage_4.amount, 'LiquidFuel')

# Подготовка к запуску и начальная ориентация
vessel.control.throttle = 1.0
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(90, 90)
# Обратный отсчёт
print('До старта осталось 3...')
time.sleep(1)
print('До старта осталось 2...')
time.sleep(1)
print('До старта осталось 1...')
print('Запуск')
flight_start_time = time.time()
vessel.control.activate_next_stage()
current_booster = 6 # Текущий твердотопливный ускоритель
while True:
    if current_booster:
        if current_booster == 6:
            if liquid_fuel_6() < 0.1:
                current_booster = 5
                vessel.control.activate_next_stage()
                print('Ускорители шестой ступени отделены')
        elif current_booster == 5:
            if liquid_fuel_5() < 0.1:
                current_booster = 4
                vessel.control.activate_next_stage()
                print('Ускорители пятой ступени отделены')
        elif current_booster == 4:
            if liquid_fuel_4() < 0.1:
                current_booster = 0
                vessel.control.activate_next_stage()
                print('Ускорители четвёртой ступени отделены')
    elapsed_time = time.time() - flight_start_time
    # Оценка доступного delta v
    dry_mass = vessel.dry_mass
    wet_mass = mass()
    isp = vessel.specific_impulse * 9.82
    if wet_mass > dry_mass and isp > 0:
        available_delta_v = isp * math.log(wet_mass / dry_mass)
    else:
        available_delta_v = 0

    telemetry_writer.writerow([
        round(elapsed_time, 3),
        round(altitude(), 1),
        round(speed(), 1),
        round(wet_mass, 3),
        round(available_delta_v, 1)
    ])
    # Расчёт гравитационного разворота
    if altitude() < altitude_start:
        target_angle = 90
    elif altitude() < target_altitude:
        gravity_turn = (altitude() - altitude_start) / (target_altitude - altitude_start)
        target_angle = max(10.0, 90.0 - gravity_turn * 80.0)
    elif apoapsis() < target_orbit * 0.9:
        target_angle = 7
    else:
        target_angle = 0
    vessel.auto_pilot.target_pitch_and_heading(target_angle, 0)
    # Отделение спутника
    if apoapsis() > target_orbit - 1000:
        print('Целевая высота апоцентра достигнута, сброс центрального блока и обтекателя, выключение двигателя')
        vessel.control.throttle = 0
        for stage in range(3):
            time.sleep(1)
            vessel.control.activate_next_stage()
        break
    time.sleep(0.1)

# Планирование импульса формирования круговой орбиты (используя уравнение vis-viva)
print('Планирование импульса формирования круговой орбиты')
mu = vessel.orbit.body.gravitational_parameter
r = vessel.orbit.apoapsis
a1 = vessel.orbit.semi_major_axis
a2 = r
v1 = math.sqrt(mu*((2./r)-(1./a1)))
v2 = math.sqrt(mu*((2./r)-(1./a2)))
delta_v = v2 - v1
node = vessel.control.add_node(
    ut() + vessel.orbit.time_to_apoapsis, prograde=delta_v)

# Подсчёт времени работы двигателей (формула Циолковского)
F = vessel.available_thrust
Isp = vessel.specific_impulse * 9.82
m0 = vessel.mass
m1 = m0 / math.exp(delta_v/Isp)
flow_rate = F / Isp
burn_time = (m0 - m1) / flow_rate
# Ориентирование ракеты
print('Ориентирование ракеты для придания импульса')
vessel.auto_pilot.reference_frame = node.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.auto_pilot.wait()

# Формирование круговой орбиты
print('Ожидание начала манёвра')
burn_ut = ut() + vessel.orbit.time_to_apoapsis - (burn_time/2.)
lead_time = 5
conn.space_center.warp_to(burn_ut - lead_time)
print('Готовность к манёвру')
time_to_apoapsis = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
while time_to_apoapsis() - (burn_time/2.) > 0:
    pass
print('Начало манёвра')
vessel.control.throttle = 1.0
time.sleep(burn_time - 0.1)
print('Точная регулировка')
vessel.control.throttle = 0.05
remaining_burn = conn.add_stream(node.remaining_burn_vector, node.reference_frame)
while apoapsis() - periapsis() > 2000:
    pass
vessel.control.throttle = 0.0
node.remove()
print('Раскрытие солнечных панелей')
vessel.control.solar_panels = True
print('Выведение спутника на полярную орбиту завершено')
telemetry_csv.close()
print(f'Телеметрия сохранена в {telemetry_file}')


# Сбор точек
interval = 0.001
point_data = {}
file = f'height_map_{datetime.datetime.now().strftime("%d-%m-%Y")}.csv'
latitude = conn.add_stream(getattr, vessel.flight(), 'latitude')
longitude = conn.add_stream(getattr, vessel.flight(), 'longitude')
surface_altitude = conn.add_stream(getattr, vessel.flight(), 'surface_altitude')
total_collected = 0
start = time.time()
while len(point_data) < 20_000:
    try:
        lat = latitude()
        lon = longitude()
        mean = altitude()
        surface = surface_altitude()
        terrain = mean - surface
        key = (round(lat, 3), round(lon, 3))
        if key not in point_data or mean < point_data[key]['Высота над уровнем моря']:
            point_data[key] = {
                        'Широта': lat,
                        'Долгота': lon,
                        'Высота над уровнем моря': mean,
                        'Высота над поверхностью': surface,
                        'Высота рельефа': terrain
            }
        total_collected += 1
        if total_collected % 1000 == 0:
            print(f'Всего собрано {total_collected}, из них уникальных {len(point_data)}, прошло времени: {time.time() - start}')
        time.sleep(interval)
    except KeyboardInterrupt:
        print('Сбор точек прерван')
        break

with open(file, 'w', newline='') as csv_file:
    fieldnames = ['Широта', 'Долгота', 'Высота над уровнем моря', 'Высота над поверхностью', 'Высота рельефа']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(list(point_data.values()))
    print('Данные сохранены')
