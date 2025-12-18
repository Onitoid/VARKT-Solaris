import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from scipy.interpolate import interp1d

# Путь к файлу телеметрии
telemetry_file = 'C:/Users/Onitoid/Downloads/telemetry_18-12-2025_14-44-05.csv'

# Чтение данных
times, heights, speeds, masses, delta_vs = [], [], [], [], []

with open(telemetry_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        times.append(float(row['Время']))
        heights.append(float(row['Высота']))
        speeds.append(float(row['Скорость']))
        masses.append(float(row['Масса']))
        delta_vs.append(float(row['Доступный delta_v']))

# Параметры модели
g0 = 9.81  # м/с²
initial_mass = 128955.0  # кг
# Используем усреднённые значения Isp и тяги
avg_isp = 320.0  # эффективный Isp в среднем
avg_thrust = 1500000.0  # (Н) средняя тяга

# Оцениваем сухую массу из последних данных в телеметрии
dry_mass = masses[-1]

# Моделирование
dt = 0.1  # шаг интегрирования
t_max = times[-1]
model_times = []
model_heights = []
model_speeds = []
model_masses = []
model_delta_vs = []

t = 0.0
h = 0.0
v = 0.0
m = initial_mass

while t <= t_max:
    # Обновление времени
    model_times.append(t)
    model_heights.append(h)
    model_speeds.append(v)
    model_masses.append(m)
    
    # Доступный delta_v по Циолковскому
    if m > dry_mass:
        delta_v_est = avg_isp * g0 * np.log(m / dry_mass)
    else:
        delta_v_est = 0.0
    model_delta_vs.append(delta_v_est)
    
    # Расход топлива: из уравнения Циолковского dm/dt = Thrust / (Isp * g0)
    if m > dry_mass:
        mdot = avg_thrust / (avg_isp * g0)
        # Ограничение, чтобы не уйти ниже dry_mass
        if m - mdot * dt < dry_mass:
            mdot = (m - dry_mass) / dt
    else:
        mdot = 0.0
    
    # Ускорение: a = (Thrust / m) - g
    if m > 0:
        a = avg_thrust / m - g0
    else:
        a = 0.0
    
    # Интегрирование (метод Эйлера)
    v += a * dt
    h += v * dt
    m -= mdot * dt
    
    # Обрезка массы на сухую массу
    if m < dry_mass:
        m = dry_mass
    
    t += dt

# Построение графиков

def plot_comparison(x_real, y_real, x_model, y_model, title, xlabel, ylabel, filename, y_major_step):
    plt.figure(figsize=(10, 5))
    plt.plot(x_real, y_real, color='tab:blue', linewidth=1.2, label='Реальные данные')
    plt.plot(x_model, y_model, color='red', linewidth=1.2, linestyle='--', label='Модель')
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim(left=0)
    plt.gca().yaxis.set_major_locator(MultipleLocator(y_major_step))
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)

# График скорости
plot_comparison(
    times, speeds,
    model_times, model_speeds,
    'Скорость от времени', 'Время (с)', 'Скорость (м/с)',
    telemetry_file.replace('.csv', '_speed_comparison.png'),
    250
)

# График высоты
plot_comparison(
    times, heights,
    model_times, model_heights,
    'Высота от времени', 'Время (с)', 'Высота (м)',
    telemetry_file.replace('.csv', '_altitude_comparison.png'),
    5000
)

# График delta-v
plot_comparison(
    times, delta_vs,
    model_times, model_delta_vs,
    'Доступный ∆v от времени', 'Время (с)', '∆v (м/с)',
    telemetry_file.replace('.csv', '_delta_v_comparison.png'),
    250
)

# График массы
plot_comparison(
    times, masses,
    model_times, model_masses,
    'Масса от времени', 'Время (с)', 'Масса (кг)',
    telemetry_file.replace('.csv', '_mass_comparison.png'),
    10000
)

# Сводный график
plt.figure(figsize=(12, 10))

# Скорость
plt.subplot(2, 2, 1)
plt.plot(times, speeds, color='tab:blue', linewidth=1.2, label='Реальные данные')
plt.plot(model_times, model_speeds, color='red', linewidth=1.2, linestyle='--', label='Модель')
plt.title('Скорость')
plt.xlabel('Время (с)')
plt.ylabel('Скорость (м/с)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
# Высота
plt.subplot(2, 2, 2)
plt.plot(times, heights, color='tab:green', linewidth=1.2, label='Реальные данные')
plt.plot(model_times, model_heights, color='red', linewidth=1.2, linestyle='--', label='Модель')
plt.title('Высота')
plt.xlabel('Время (с)')
plt.ylabel('Высота (м)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

# Delta-v
plt.subplot(2, 2, 3)
plt.plot(times, delta_vs, color='tab:red', linewidth=1.2, label='Реальные данные')
plt.plot(model_times, model_delta_vs, color='red', linewidth=1.2, linestyle='--', label='Модель')
plt.title('Доступный ∆v')
plt.xlabel('Время (с)')
plt.ylabel('∆v (м/с)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

# Масса
plt.subplot(2, 2, 4)
plt.plot(times, masses, color='tab:purple', linewidth=1.2, label='Реальные данные')
plt.plot(model_times, model_masses, color='orange', linewidth=1.2, linestyle='--', label='Модель')
plt.title('Масса')
plt.xlabel('Время (с)')
plt.ylabel('Масса (кг)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

plt.tight_layout()
plt.savefig(telemetry_file.replace('.csv', '_all_comparison.png'), dpi=150)

plt.show()

# Интерполяция модели на точки реальных данных
interp_speed = interp1d(model_times, model_speeds, kind='linear', fill_value="extrapolate")
interp_height = interp1d(model_times, model_heights, kind='linear', fill_value="extrapolate")
interp_delta_v = interp1d(model_times, model_delta_vs, kind='linear', fill_value="extrapolate")
