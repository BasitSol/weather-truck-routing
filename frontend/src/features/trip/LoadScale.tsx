import { useId } from 'react'
import { MAX_LOAD_LB, NO_TRAVEL_RULE_LB, SEVERE_RULE_LB, activeLoadRules, formatLb, parseLb } from '../../lib/load'

const PRESETS = [20_000, 35_000, 45_000, 80_000]
const pct = (lb: number) => `${(lb / MAX_LOAD_LB) * 100}%`

interface Props {
  text: string
  onChange: (text: string) => void
  error?: string
}

/**
 * Load weight on a white sign plate. The bar marks the two weights where the brief's load rules
 * start to apply, and the lamps beneath say which rules this load switches on.
 */
export function LoadScale({ text, onChange, error }: Props) {
  const id = useId()
  const lb = parseLb(text)
  const value = lb === null ? 0 : Math.min(Math.max(lb, 0), MAX_LOAD_LB)
  const rules = activeLoadRules(value)
  const ruleCount = Number(rules.noTravelAbove45) + Number(rules.severeAbove35)

  return (
    <div className="field load-scale">
      <div className="board" role="group" aria-labelledby={`${id}-label`} aria-describedby={`${id}-help`}>
        <div className="board-head">
          <label id={`${id}-label`} htmlFor={`${id}-lb`} className="board-label">
            Load weight
          </label>
          <span className="board-caption">Load rules switch on above 30,000 and 40,000 lb</span>
        </div>
        <div className="board-readout">
          <input
            id={`${id}-lb`}
            className="board-input figure"
            inputMode="numeric"
            autoComplete="off"
            aria-invalid={Boolean(error)}
            value={text}
            onChange={(e) => onChange(e.target.value)}
            onBlur={() => lb !== null && onChange(formatLb(lb))}
          />
          <span className="board-unit figure">lb</span>
        </div>

        <div className="scale">
          {/* Rule thresholds, labelled on the axis; each lights once the load crosses it. */}
          <div className="scale-marks figure" aria-hidden>
            <span className="scale-mark" data-on={rules.noTravelAbove45} style={{ left: pct(NO_TRAVEL_RULE_LB) }}>
              30k
            </span>
            <span className="scale-mark" data-on={rules.severeAbove35} style={{ left: pct(SEVERE_RULE_LB) }}>
              40k
            </span>
          </div>
          <div className="scale-track" aria-hidden>
            <span className="scale-zone" style={{ left: pct(NO_TRAVEL_RULE_LB), width: pct(SEVERE_RULE_LB - NO_TRAVEL_RULE_LB) }} />
            <span className="scale-zone scale-zone-strong" style={{ left: pct(SEVERE_RULE_LB), right: 0 }} />
            <span className="scale-fill" style={{ width: pct(value) }} />
            <span className="scale-threshold" data-on={rules.noTravelAbove45} style={{ left: pct(NO_TRAVEL_RULE_LB) }} />
            <span className="scale-threshold" data-on={rules.severeAbove35} style={{ left: pct(SEVERE_RULE_LB) }} />
          </div>
          <input
            type="range"
            className="scale-range"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={value}
            aria-label="Load weight"
            aria-valuetext={`${formatLb(value)} pounds, ${ruleCount === 0 ? 'no load rules apply' : `${ruleCount} load rule${ruleCount > 1 ? 's' : ''} apply`}`}
            onChange={(e) => onChange(formatLb(Number(e.target.value)))}
          />
          <div className="scale-ends figure" aria-hidden>
            <span>0</span>
            <span>80k</span>
          </div>
        </div>

        <ul className="load-rules" id={`${id}-help`}>
          <li data-active={rules.noTravelAbove45}>
            <span className="lamp" data-level={4} aria-hidden />
            <span>
              Wind 45 to 54 mph is <strong>No Travel</strong> over <span className="tnum">30,000</span> lb
            </span>
            <span className="rule-state">{rules.noTravelAbove45 ? 'On' : 'Off'}</span>
          </li>
          <li data-active={rules.severeAbove35}>
            <span className="lamp" data-level={3} aria-hidden />
            <span>
              Wind 35 to 44 mph is <strong>Severe</strong> over <span className="tnum">40,000</span> lb
            </span>
            <span className="rule-state">{rules.severeAbove35 ? 'On' : 'Off'}</span>
          </li>
        </ul>
      </div>

      <div className="scale-presets">
        <span className="scale-presets-caption">Presets</span>
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            className="scale-preset figure"
            aria-pressed={value === p}
            onClick={() => onChange(formatLb(p))}
          >
            {formatLb(p)}
          </button>
        ))}
      </div>
      {error && <p className="field-error">{error}</p>}
    </div>
  )
}
