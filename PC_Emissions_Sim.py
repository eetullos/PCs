#Intermittent Bleed Pneumatic Controller Simulator v1.0

import numpy as np

def simulate_emissions_optimized(PC_count, DTF, S0, timesteps, p_gas, S1, p, r, prop_rates, malf_rates):
    # Conversion factor from scfh to metric tons per day
    scfh_to_metric_tons_per_day = 24 * p_gas

    # Validate parameters
    if not (0 <= S0 <= 1):
        raise ValueError(f"Invalid S0: {S0}")
    if not (0 < DTF):
        raise ValueError(f"Invalid DTF: {DTF}")

    # Clip transition probabilities
    p = np.clip(p, 0, 1)
    r = np.clip(r, 0, 1)

    # Sample PC-specific emission rates
    prop_sample = np.random.choice(prop_rates, size=PC_count)
    malf_sample = np.random.choice(malf_rates, size=PC_count)

    # Initial states: 0 = properly operating, 1 = malfunctioning
    states = np.random.choice([0, 1], size=PC_count, p=[S0, S1])

    # Preallocate output arrays
    emission_rates_each = np.zeros((timesteps, PC_count))
    state_history = np.zeros((timesteps, 2))
    state_history_each = np.zeros((timesteps, PC_count))

    # Transition matrix
    P = np.array([[1 - p, p],
                  [r, 1 - r]])

    for t in range(timesteps):
        # Record current states
        state_history_each[t] = states
        state_counts = np.bincount(states, minlength=2) / PC_count
        state_history[t] = state_counts

        # Assign emission rates for this timestep
        emissions = np.where(states == 0, prop_sample, malf_sample)
        emission_rates_each[t] = emissions

        # Transition: use random values and threshold logic for faster state updates
        rand_vals = np.random.rand(PC_count)
        next_states = np.where(
            (states == 0) & (rand_vals < p), 1,
            np.where((states == 1) & (rand_vals < r), 0, states)
        )
        states = next_states

    # Emission summaries
    avg_emission_rate = np.mean(emission_rates_each, axis=1)
    all_avg_emission_rate = np.mean(avg_emission_rate)
    sum_emission_rate = np.sum(emission_rates_each, axis=1)
    cumulative_emission = np.cumsum(sum_emission_rate) * scfh_to_metric_tons_per_day
    final_cumulative_emission = cumulative_emission[-1]

    return (emission_rates_each, avg_emission_rate, all_avg_emission_rate,
            sum_emission_rate, cumulative_emission, final_cumulative_emission,
            state_history, state_history_each)
