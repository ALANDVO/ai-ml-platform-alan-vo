import React from 'react';
import { HyperparamSpec } from '../api/client';

interface Props {
  spec: HyperparamSpec;
  value: number | string;
  onChange: (value: number | string) => void;
}

export default function HyperparamSlider({ spec, value, onChange }: Props) {
  if (spec.type === 'categorical') {
    return (
      <div className="slider-row">
        <label className="slider-label">{spec.name}</label>
        <select
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          className="slider-select"
        >
          {(spec.choices || []).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <span className="slider-value">{String(value)}</span>
      </div>
    );
  }

  const isLog = spec.type === 'logfloat';
  const low = spec.low ?? 0;
  const high = spec.high ?? 1;
  const step = (high - low) / 100;

  let displayVal: number;
  if (isLog) {
    const base = 10;
    const logLow = Math.log10(low);
    const logHigh = Math.log10(high);
    const logVal = Math.log10(Number(value));
    displayVal = low * (base ** ((logVal - logLow) / (logHigh - logLow)));
    displayVal = Number(value);
  } else {
    displayVal = Number(value);
  }

  return (
    <div className="slider-row">
      <label className="slider-label">{spec.name}</label>
      <input
        type="range"
        min={low}
        max={high}
        step={step}
        value={Number(value)}
        onChange={(e) => onChange(Number(e.target.value))}
        className="slider-input"
      />
      <span className="slider-value">
        {displayVal >= 0.01 ? displayVal.toFixed(4) : displayVal.toExponential(2)}
      </span>
    </div>
  );
}
