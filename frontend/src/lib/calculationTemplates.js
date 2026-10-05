// Example `inputs` payloads for each OIML test code, read directly from the
// docstrings/validation logic in backend/app/services/calculation_engine/*.py
// on the jaadu branch. WP, ZR, TEMP_STATIC, TEMP_NO_LOAD, ECC_WEIGHT and REP get
// dedicated forms in TestSessionDetail.jsx;
// everything else falls back to a JSON textarea pre-filled with these
// templates, since each test's exact shape/cardinality is quite specific
// (e.g. REP needs exactly 2 series of exactly 10 measurements each) and
// building a dedicated widget for all 12 wasn't practical in one pass.
//
// IMPORTANT: as of this snapshot, the backend does NOT convert these JSON
// numbers into Python Decimal before running the engine, and every
// calculation function strictly requires true Decimal instances — so
// submitting any of these will currently fail with something like
// "indicated_value must be a Decimal" until that's fixed server-side
// (see the note left for the backend team).

export const TEST_INPUT_TEMPLATES = {
  WP: { measurements: [{ load: 10, indication: 10.01, additional_load: 0, zero_error: 0 }] },

  ZR: { load: 25, zero_before: 0, zero_after: 0.004, automatic_zero_tracking_disabled: true },

  TEMP_STATIC: {
    load: 10,
    observations: [
      { temperature: 20, loading: { indicated_value: 10.01, additional_load: 0, zero_error: 0 }, unloading: { indicated_value: 0.0, additional_load: 0, zero_error: 0 } },
      { temperature: 40, loading: { indicated_value: 10.01, additional_load: 0, zero_error: 0 }, unloading: { indicated_value: 0.0, additional_load: 0, zero_error: 0 } },
      { temperature: -10, loading: { indicated_value: 10.01, additional_load: 0, zero_error: 0 }, unloading: { indicated_value: 0.0, additional_load: 0, zero_error: 0 } },
      { temperature: 5, loading: { indicated_value: 10.01, additional_load: 0, zero_error: 0 }, unloading: { indicated_value: 0.0, additional_load: 0, zero_error: 0 } },
      { temperature: 20, loading: { indicated_value: 10.01, additional_load: 0, zero_error: 0 }, unloading: { indicated_value: 0.0, additional_load: 0, zero_error: 0 } },
    ],
  },

  TEMP_NO_LOAD: {
    observations: [
      { temperature: 20, zero_error: 0 },
      { temperature: 40, zero_error: 0.001 },
      { temperature: -10, zero_error: 0.002 },
    ],
  },

  ECC_WEIGHT: {
    // load must equal Max/3 for the prototype instrument on all 4 positions
    measurements: [
      { position: "FRONT_LEFT", load: 10, indication: 10.0, additional_load: 0, zero_error: 0 },
      { position: "FRONT_RIGHT", load: 10, indication: 10.0, additional_load: 0, zero_error: 0 },
      { position: "REAR_LEFT", load: 10, indication: 10.0, additional_load: 0, zero_error: 0 },
      { position: "REAR_RIGHT", load: 10, indication: 10.0, additional_load: 0, zero_error: 0 },
    ],
  },

  REP: {
    series: [
      { series_id: "50_PERCENT_MAX", measurements: Array.from({ length: 10 }, () => ({ load: 15, indication: 15.0, additional_load: 0 })) },
      { series_id: "100_PERCENT_MAX", measurements: Array.from({ length: 10 }, () => ({ load: 30, indication: 30.0, additional_load: 0 })) },
    ],
  },

  DIS: {
    // loads must be exactly [Min, Max/2, Max] in that order
    loads: [
      { load: 0.2, initial_indication: 0.2, decreased_indication: 0.19, increased_indication: 0.21 },
      { load: 15, initial_indication: 15.0, decreased_indication: 14.99, increased_indication: 15.01 },
      { load: 30, initial_indication: 30.0, decreased_indication: 29.99, increased_indication: 30.01 },
    ],
  },

  CRP: {
    load: 30,
    // either 4 readings (early termination at 30 min) or all 8 (full 4-hour test)
    readings: [
      { time_minutes: 0, indication: 30.0, additional_load: 0 },
      { time_minutes: 5, indication: 30.0, additional_load: 0 },
      { time_minutes: 15, indication: 30.0, additional_load: 0 },
      { time_minutes: 30, indication: 30.0, additional_load: 0 },
    ],
    temperatures: [20, 20, 20, 20],
  },

  TARE: {
    tare_value: 10,
    maximum_tare: 15,
    loading_measurements: Array.from({ length: 5 }, (_, i) => ({ load: (i + 1) * 4, indication: (i + 1) * 4, additional_load: 0, zero_error: 0 })),
    unloading_measurements: Array.from({ length: 5 }, (_, i) => ({ load: (5 - i) * 4, indication: (5 - i) * 4, additional_load: 0, zero_error: 0 })),
  },

  WARMUP: {
    power_off_hours: 8,
    load: 28,
    observations: [
      { elapsed_minutes: 5, indication: 28.0, zero_error: 0, additional_load: 0 },
      { elapsed_minutes: 15, indication: 28.0, zero_error: 0, additional_load: 0 },
      { elapsed_minutes: 30, indication: 28.0, zero_error: 0, additional_load: 0 },
    ],
  },

  VOLT: {
    load: 0.1, // must equal e * 10 for the instrument under test
    observations: [
      { voltage: 195.5, indication: 0.1, additional_load: 0, zero_error: 0 },
      { voltage: 230, indication: 0.1, additional_load: 0, zero_error: 0 },
      { voltage: 253, indication: 0.1, additional_load: 0, zero_error: 0 },
    ],
  },

  SPAN: {
    load: 28,
    power_disconnections: [8, 8],
    initial_readings: Array.from({ length: 5 }, () => ({ indication: 28.0, additional_load: 0, zero_error: 0 })),
    measurements: Array.from({ length: 8 }, () => ({ indication: 28.0, additional_load: 0, zero_error: 0 })),
  },
};

export const DEDICATED_FORM_TEST_CODES = ["WP", "ZR", "TEMP_STATIC", "TEMP_NO_LOAD", "ECC_WEIGHT", "REP"];
