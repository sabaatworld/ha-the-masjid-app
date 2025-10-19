class PrayerTimesCard extends HTMLElement {
  constructor() {
    super();
    this.holdTimer = null;
    this.startX = 0;
    this.startY = 0;
  }

  connectedCallback() {
    this.addEventListener('pointerdown', this._handlePointerDown.bind(this));
    this.addEventListener('pointerup', this._handlePointerUp.bind(this));
    this.addEventListener('pointermove', this._handlePointerMove.bind(this));
    this.addEventListener('pointercancel', this._handlePointerUp.bind(this));
  }

  disconnectedCallback() {
    this.removeEventListener('pointerdown', this._handlePointerDown.bind(this));
    this.removeEventListener('pointerup', this._handlePointerUp.bind(this));
    this.removeEventListener('pointermove', this._handlePointerMove.bind(this));
    this.removeEventListener('pointercancel', this._handlePointerUp.bind(this));
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content prayer-times-card-content">
            <div id="prayers"></div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector('#prayers');
    }

    if (!this.config || !this.config.masjid) {
      this.content.innerHTML = "Error: Please select a Masjid in the card configuration.";
      return;
    }

    if (!this._entities) {
      this.content.innerHTML = "Loading...";
      this._updateEntities();
      return;
    }

    const prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'];

    const formatTime = (time) => {
      if (!time || time === 'unavailable' || time === 'unknown' || time === 'None') {
        return '—';
      }
      return time;
    };

    const prayer_times = prayers.map(prayer => {
        const azan_entity = this._entities[`${prayer}_azan`];
        const iqama_entity = this._entities[`${prayer}_iqama`];
        const azan_time = azan_entity && hass.states[azan_entity] ? hass.states[azan_entity].state : '-';
        const iqama_time = iqama_entity && hass.states[iqama_entity] ? hass.states[iqama_entity].state : '-';
        return {
            name: prayer.charAt(0).toUpperCase() + prayer.slice(1),
            azan: formatTime(azan_time),
            iqama: formatTime(iqama_time)
        };
    });

    // Add Sunrise
    const sun_entity = hass.states['sun.sun'];
    let sunrise_time = '—';
    if (sun_entity && sun_entity.attributes.next_rising) {
        const sunrise_date = new Date(sun_entity.attributes.next_rising);
        let hours = sunrise_date.getHours();
        const minutes = sunrise_date.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12; // the hour '0' should be '12'
        const hoursStr = hours.toString().padStart(2, '0');
        sunrise_time = `${hoursStr}:${minutes} ${ampm}`;
    }

    prayer_times.splice(1, 0, {
        name: 'Sunrise',
        azan: sunrise_time,
        iqama: '—'
    });


    this.content.innerHTML = `
      <style>
        .prayer-table {
          width: 100%;
          border-collapse: collapse;
        }
        .prayer-table th {
          text-align: center;
          padding: 0.125em;
          letter-spacing: 0.0625em;
          font-size: 0.9em;
        }
        .prayer-table td {
          text-align: center;
          padding: 0.125em;
          font-size: 0.9em;
        }
        .prayer-times-card-content {
          padding: 12px
        }
      </style>
      <table class="prayer-table">
        <thead>
          <tr>
            ${prayer_times.map(p => `<th>${p.name}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          <tr>
            ${prayer_times.map(p => `<td>${p.azan}</td>`).join('')}
          </tr>
          <tr>
            ${prayer_times.map(p => `<td>${p.iqama}</td>`).join('')}
          </tr>
        </tbody>
      </table>
    `;
  }

  async _updateEntities() {
    const registryEntities = await this._hass.callWS({
      type: "config/entity_registry/list"
    });
    const deviceEntities = registryEntities.filter(e => e.device_id === this.config.masjid);

    this._entities = {};
    const prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'];
    prayers.forEach(prayer => {
      const azan = deviceEntities.find(e => e.entity_id.endsWith(`_${prayer}_azan`));
      const iqama = deviceEntities.find(e => e.entity_id.endsWith(`_${prayer}_iqama`));
      if (azan) this._entities[`${prayer}_azan`] = azan.entity_id;
      if (iqama) this._entities[`${prayer}_iqama`] = iqama.entity_id;
    });

    if (!this._entities.fajr_azan) {
      this.content.innerHTML = `Error: Could not find prayer time entities for the selected Masjid.`;
      return;
    }
    this._entityId = this._entities.fajr_azan;
    this.hass = this._hass;
  }

  _handlePointerDown(e) {
    this.startX = e.clientX;
    this.startY = e.clientY;
    this.holdTimer = setTimeout(() => {
      this._handleHold();
    }, 500);
  }

  _handlePointerUp(e) {
    clearTimeout(this.holdTimer);
  }

  _handlePointerMove(e) {
    if (this.holdTimer) {
      const deltaX = Math.abs(e.clientX - this.startX);
      const deltaY = Math.abs(e.clientY - this.startY);
      if (deltaX > 10 || deltaY > 10) {
        clearTimeout(this.holdTimer);
        this.holdTimer = null;
      }
    }
  }

  _handleHold() {
    if (!this.config || !this._hass || !this._entityId) {
      return;
    }
    const entityId = this._entityId;
    this._hass.callWS({
      type: 'config/entity_registry/get',
      entity_id: entityId,
    }).then((entity) => {
      if (entity && entity.device_id) {
        window.location.href = `/config/devices/device/${entity.device_id}`;
      }
    });
  }

  setConfig(config) {
    if (!config.masjid) {
      throw new Error('You need to select a Masjid');
    }
    this.config = config;
    this._entities = null; // Reset entities when config changes
    this._entityId = null;
  }

  getCardSize() {
    return 3;
  }

  static async getConfigForm() {
    return {
      schema: [
        {
          name: 'masjid',
          required: true,
          selector: {
            device: {
              integration: 'ha_the_masjid_app'
            }
          }
        },
      ],
      computeHelper: (schema) => {
        if (schema.name === 'masjid') {
          return 'Select the Masjid to display prayer times for.';
        }
        return undefined;
      },
    };
  }

  static getStubConfig() {
    return { masjid: '' };
  }
}

customElements.define('prayer-times-card', PrayerTimesCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'prayer-times-card',
  name: 'Prayer Times Card',
  preview: false,
  description: 'A card to display prayer times.',
});
