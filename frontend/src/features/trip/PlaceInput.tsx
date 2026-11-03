import { useId, useState } from 'react'
import { usePlaceSearch } from '../../api/client'
import type { Place } from '../../api/types'

interface Props {
  label: string
  /** Which map marker this row wears: the filled Start dot or the Destination ring. */
  role: 'origin' | 'destination'
  value: Place | null
  onChange: (place: Place | null) => void
  bias: Place | null
  error?: string
}

/** Typeahead over /geocode, following the ARIA combobox pattern (list + active descendant). */
export function PlaceInput({ label, role, value, onChange, bias, error }: Props) {
  const id = useId()
  const [text, setText] = useState(value?.label ?? '')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [lastValue, setLastValue] = useState(value)

  // Keep the text in step when the place is set from outside (swap, sample trips).
  if (value !== lastValue) {
    setLastValue(value)
    setText(value?.label ?? '')
  }

  const search = usePlaceSearch(open ? text : '', bias)
  const results = search.data ?? []
  const listId = `${id}-list`
  const showList = open && text.trim().length >= 3 && (results.length > 0 || !search.isFetching)

  function choose(place: Place) {
    onChange(place)
    setText(place.label)
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showList || results.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => (i + 1) % results.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => (i - 1 + results.length) % results.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      choose(results[Math.min(active, results.length - 1)])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="place-field" data-role={role}>
      <div className="place-row" data-invalid={Boolean(error)}>
        <span className="place-marker" data-kind={role} aria-hidden />
        <label htmlFor={id} className="place-label">
          {label}
        </label>
        <input
        id={id}
        className="place-input"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && results.length ? `${listId}-${active}` : undefined}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder="City or address"
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
          setActive(0)
          if (value) onChange(null)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      </div>
      {showList && (
        <ul id={listId} role="listbox" className="suggestions" aria-label={`${label} suggestions`}>
          {results.length === 0 && (
            <li className="suggestion-empty" role="presentation">
              {search.isError ? 'Place search is unavailable right now.' : 'No places match.'}
            </li>
          )}
          {results.map((place, i) => (
            <li
              key={`${place.label}-${place.lat}-${place.lon}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className="suggestion"
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setActive(i)}
              onClick={() => choose(place)}
            >
              {place.label}
            </li>
          ))}
        </ul>
      )}
      {error && (
        <p id={`${id}-error`} className="field-error">
          {error}
        </p>
      )}
    </div>
  )
}
