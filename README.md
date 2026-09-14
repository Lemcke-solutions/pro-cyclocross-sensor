# Pro Cyclocross Sensor

A Home Assistant custom integration that creates sensors for professional cyclocross races. All sensors are grouped under a device per competition and automatically reflect which races are happening today and which are coming up.

## How it works

The integration reads `cyclocross_races.json` (bundled in the integration directory) and creates two sensors per competition:

- **`current_cx_*`** — a race happening **today**; state is `0`
- **`next_cx_*`** — the next upcoming race; state = days until start

Race names are displayed in the language configured in your Home Assistant instance where a translation is available, otherwise the original name is shown. Sensors are grouped into devices per competition — **Pro Cyclocross — Superprestige**, **Pro Cyclocross — UCI World Cup**, **Pro Cyclocross — X2O Trofee**, **Pro Cyclocross — HG Cross** and **Pro Cyclocross — UCI World Championships** — all listed under the Lemcke Solutions manufacturer.

The UCI World Championships has separate Elite Women's and Elite Men's races on different days; each is a distinct entry in the calendar, so `next_cx_world_championships_1` automatically follows whichever race is next (women's race first, then men's).

### Sensor naming

```
sensor.{status}_cx_{series}_{slot}
```

| Part | Values |
|---|---|
| `status` | `current` or `next` |
| `series` | `superprestige`, `world_cup`, `x2o_trofee`, `hg_cross`, `world_championships` |
| `slot` | `1`, `2`, … (normally just `1`) |

**Examples:**

| Sensor | Meaning |
|---|---|
| `sensor.current_cx_superprestige_1` | Today's Superprestige race |
| `sensor.next_cx_world_cup_1` | Next upcoming UCI World Cup round |
| `sensor.next_cx_hg_cross_1` | Next upcoming HG Cross race |
| `sensor.next_cx_x2o_trofee_1` | Next upcoming X2O Trofee race |
| `sensor.next_cx_world_championships_1` | Next upcoming World Championships race (women's, then men's) |

A slot with no race assigned has state `unknown`.

### Sensor attributes

| Attribute | Description |
|---|---|
| `race_name` | Race name in your HA language |
| `series` | `superprestige`, `world_cup`, `x2o_trofee` or `hg_cross` |
| `location` | Host city and country |
| `date` | ISO date (YYYY-MM-DD) |

---

## Installation

### Manual

Copy the `custom_components/pro_cyclocross` directory to your HA `config/custom_components/` folder and restart.

### HACS

Add this repository as a custom repository in HACS, install **Pro Cyclocross Sensor**, restart Home Assistant, then go to **Settings → Integrations → Add Integration** and search for *Pro Cyclocross Sensor*.

---

## Configuration

The setup screen has no required fields. Click **Submit** to activate the integration.

---

## Automation example — Daily cyclocross briefing

Announces any race happening today, or the next upcoming race per competition otherwise.

```yaml
alias: Cyclocross daily briefing
trigger:
  - platform: time
    at: "07:00:00"
action:
  - action: notify.mobile_app_my_phone
    data:
      title: "🚲 Veldrijden update"
      message: >
        {%- set current = states.sensor
            | selectattr('entity_id', 'match', '^sensor\\.current_cx_')
            | rejectattr('state', 'in', ['unknown', 'unavailable'])
            | list -%}
        {%- if current %}
        Vandaag op de fiets:
        {%- for s in current %}
        • {{ state_attr(s.entity_id, 'race_name') }} ({{ state_attr(s.entity_id, 'location') }})
        {%- endfor %}
        {%- else %}
        Vandaag geen veldrit.
        {%- endif %}

        {%- set next_races = states.sensor
            | selectattr('entity_id', 'match', '^sensor\\.next_cx_')
            | rejectattr('state', 'in', ['unknown', 'unavailable'])
            | sort(attribute='state') | list -%}
        {%- if next_races %}

        Eerstvolgende crossen:
        {%- for s in next_races[:4] %}
        • {{ state_attr(s.entity_id, 'race_name') }} over {{ s.state }} dag{{ 'en' if s.state | int != 1 else '' }}
        {%- endfor %}
        {%- endif %}
```

---

## Race calendar

The integration ships with a bundled `cyclocross_races.json` that contains the 2026–2027 cyclocross calendar for:

- **Telenet Superprestige**
- **UCI Cyclocross World Cup**
- **X2O Badkamers Trofee**
- **HG Cross** (formerly Exact Cross)
- **UCI Cyclocross World Championships** (Elite Women and Elite Men)

### Something missing or incorrect?

If a race is missing, has wrong dates, or is categorised incorrectly, feel free to open a pull request to fix it. The file lives at `custom_components/pro_cyclocross/cyclocross_races.json` in this repository. Each entry follows this structure:

```json
{
  "name": "Koppenbergcross",
  "series": "x2o_trofee",
  "location": "Oudenaarde, Belgium",
  "date": "2026-11-01"
}
```

`series` must be one of `superprestige`, `world_cup`, `x2o_trofee`, `hg_cross` or `world_championships`.

`name` may be a plain string, or an object of per-language translations (as used for the World Championships entries) with `en` as the fallback for missing languages.

### Updating for a new season

The calendar will be updated in this repository at the start of each new season. After pulling the latest version, reload the integration via **Settings → Integrations → Pro Cyclocross Sensor → Reload**.

---

## License

MIT
