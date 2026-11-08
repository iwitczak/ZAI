const { createApp, ref, reactive, computed, onMounted, onBeforeUnmount } = Vue;

// Page components
const Home = {
  template: '#tpl-home',
  setup() {
    const measurementsFilterError = ref('');
    const measurementsFilterErrorValues = ref('');
    const loading = ref(false);

    const measurementsData = ref([]);
    const measurementsFilterData = reactive({"from": "", "to": "", "series": ""});

    const isAuthenticated = computed(() => !!auth.token);

    // TABLE
    const selectedId = ref(null);
    let indexById = new Map();

    // CHART
    const chartElement = ref(null);
    let chart = null;
    let resizeObserver = null;

    const WINDOW_MS = 60 * 60 * 1000; // 60 minutes
    let initialized = false;

    function renderChart() {
      if (!chart) return;
      const data = measurementsData.value ?? [];

      const BUILTIN_SYMBOLS = ['circle', 'rect', 'roundRect', 'triangle', 'diamond', 'pin', 'arrow'];
      const legendData = [];
      function resolveSymbol(icon) {
        if (!icon || typeof icon !== 'string') return null;
        if (BUILTIN_SYMBOLS.includes(icon)) return icon;
        return null;
      }

      indexById = new Map();

      const groups = new Map();
      for (const m of data) {
        if (!groups.has(m.seriesId)) groups.set(m.seriesId, []);
        groups.get(m.seriesId).push(m);
      }

      const series = [...groups].map(([seriesId, items], seriesIndex) => {
        const sorted = [...items].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        sorted.forEach((m, dataIndex) => indexById.set(m.id, {seriesIndex, dataIndex}))
        const color = sorted[0]?.seriesColor;
        const icon = resolveSymbol(sorted[0]?.seriesIcon);
        const name = `Series ${seriesId}`;
        legendData.push(icon ? { name, icon } : { name });
        return {
        name: name,
        type: 'line',
        symbol: icon,
        symbolSize: 8,
        itemStyle: { color },
        lineStyle: { color },
        data: items
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
          .map(m => ({ value: [m.timestamp, m.value], id: m.id, ts: m.timestamp })),
        emphasis: {
          focus: 'self',
          scale: 1.8,
          itemStyle: { borderWidth: 3, borderColor: '#000' },
        },
        }
      });

      const option = {
        tooltip: { 
          trigger: 'axis' ,
          confine: true, 
          formatter: (params) => {
            const time = params[0].data.ts;
            const rows = params.map(p =>
              `${p.marker} ${p.seriesName}: <b>${p.value[1]}</b>`
            ).join('<br>');
            return `${time}<br>${rows}`;
          },
        },
        legend: { type: 'scroll', bottom: 0, data: legendData },
        grid: { bottom: 80 },
        xAxis: { type: 'time', minInterval: 60 * 1000 },
        yAxis: { type: 'value' },
        dataZoom: [
          {
            type: 'inside',
            zoomLock: false,
            filterMode: 'none',
            minValueSpan: WINDOW_MS/60,
            maxValueSpan: WINDOW_MS*24,
          },
          {
            type: 'slider',
            zoomLock: false,
            filterMode: 'none',
            bottom: 35,
            minValueSpan: WINDOW_MS/60,
            maxValueSpan: WINDOW_MS*24,
          },
        ],
        series,
      };

      // Initial window size
      if (!initialized && data.length) {
        const end = data.reduce((mx, m) => Math.max(mx, new Date(m.timestamp).getTime()), 0);
        option.dataZoom.forEach(z => { z.endValue = end; z.startValue = end - WINDOW_MS; });
        initialized = true;
      }

      chart.setOption(option, { replaceMerge: ['series'] });
    }

    function selectRow(m) {
      const pos = indexById.get(m.id);
      if (!pos || !chart) return;

      selectedId.value = m.id;

      // Move window if record not in view
      const t = new Date(m.timestamp).getTime();
      chart.dispatchAction({
        type: 'dataZoom',
        startValue: t - WINDOW_MS / 2,
        endValue: t + WINDOW_MS / 2,
      });

      chart.dispatchAction({ type: 'downplay' });
      chart.dispatchAction({ type: 'highlight', ...pos });
      chart.dispatchAction({ type: 'showTip', ...pos });
    }

    onMounted(() => {
      chart = echarts.init(chartElement.value);
      renderChart();
      resizeObserver = new ResizeObserver(() => chart?.resize());
      resizeObserver.observe(chartElement.value);
      getMeasurements();
    });

    Vue.watch(measurementsData, renderChart);

    onBeforeUnmount(() => {
      resizeObserver?.disconnect();
      chart?.dispose();
    });
    // // CHART

    async function getMeasurements() {
      loading.value = true;
      try {
        measurementsData.value = await api(
          path = '/measurements',
          {method: 'GET', params: measurementsFilterData, auth: false}
        );
        console.log(measurementsData);
      } catch (e) {
        measurementsFilterError.value = e;
        measurementsFilterErrorValues.value = e?.errors;
      } finally {
        loading.value = false;
      }
    }

    return {
      measurementsFilterError, measurementsFilterErrorValues, loading, isAuthenticated,
      measurementsData, measurementsFilterData,
      getMeasurements, selectRow, selectedId, 
      chartElement
    }
  }

};

const UserLogin = {
  template: '#tpl-user-login',
  setup() {
    const credentials = reactive({username: '', password: ''});
    const error = ref('');
    const isAuthenticated = computed(() => !!auth.token);

    async function login() {
      try {
        const data = await api('/auth/login', {
          method: 'POST', body: { ...credentials }, auth: false,
        });
        auth.login(data.accessToken, credentials.username, Date.now() + data.expiresIn * 1000);
        credentials.password = '';
        state.page = 'home';
      } catch (e) {
        error.value = e.message;
      }
    }
    return { error, login, credentials, isAuthenticated };
  }
};

const UserChangePassword = {
  template: '#tpl-user-change-password',
  setup() {
    const passwords = reactive({currentPassword: '', newPassword: ''});
    const error = ref('');
    const isAuthenticated = computed(() => !!auth.token);

    async function changePassword() {
      try {
        const data = await api('/auth/password', {
          method: 'PUT', body: { ...passwords }, auth: true,
        });
        auth.logout();
        state.page = 'home';
      } catch (e) {
        error.value = e.message;
      }
    }
    return { error, changePassword, passwords, isAuthenticated };
  }
};

const ManageSensors = {
  template: '#tpl-manage-sensors',
  setup() {
    const error = ref('');
    const response = ref('');
    const loading = ref(false);
    const sensorData  = reactive({});

    const newSensorData = reactive({"name": "", "seriesId": ""});
    const newSensorKey = ref('');
    const newSensorAddError = ref('');
    const newSensorAddErrorValues = ref({});

    const isAuthenticated = computed(() => !!auth.token);

    async function getSensors() {
      try {
        loading.value = true;
        error.value = '';
        sensorData.value = await api(
          '/sensors', {
            method: 'GET',
            auth: true
          });
      } catch (e) {
        error.value = e
      } finally {
        loading.value= false;
      }
    }

    async function registerSensor() {
      loading.value = true;
      newSensorKey.value = '';
      newSensorAddError.value = '';

      try {
        const data = await api(
          '/sensors',
          {method: 'POST', body: {...newSensorData}, auth: true}
        );
        console.log(data);
        console.log(data.apiKey);
        newSensorKey.value = data.apiKey
      } catch (e) {
        newSensorAddError.value = e;
        console.log(e.status);                  // 400, 404, 422...
        console.log(e.problem.type);            // URI typu problemu
        console.log(e.problem.title);
        newSensorAddErrorValues.value = e.errors;
      } finally {
        loading.value = false;
        await getSensors();
      }
    }

    function registerSensorFormClear() {
      Object.assign(newSensorData, {"name": "", "seriesId": ""});
      newSensorKey.value = '';
      newSensorAddError.value = '';
      console.log("cleared");
    }

    async function unregisterSensor(id) {
      console.log(id);
      try {
        loading.value = true;
        error.value = '';
        _ = await api(
          `/sensors/${id}`, {
            method: 'DELETE',
            auth: true
          });
        sensorData.value = await api(
          '/sensors', {
            method: 'GET',
            auth: true
          });
      } catch (e) {
        error.value = e
      } finally {
        loading.value= false;
      }
    }

   return { 
    error, response, loading, sensorData, isAuthenticated,
    newSensorKey, newSensorAddError, newSensorData, newSensorAddErrorValues,
    getSensors, registerSensor, unregisterSensor, registerSensorFormClear
  } 
  }
  
};

const ManageSeries = {
  template: '#tpl-manage-series',
  setup() {
    const error = ref('');
    const response = ref('');
    const loading = ref(false);
    const seriesData  = reactive({});
    const modalEditSeries = ref(null);
    let modal = null;

    const newSeriesData = reactive({"name": "", "minValue": 0, "maxValue": 0, "color": "#000000", "unit": undefined, "icon": undefined});
    const newSeriesId = ref('');
    const newSeriesAddError = ref('');
    const newSeriesAddErrorValues = ref({});

    const editSeriesData = reactive({"id": "", "name": "", "minValue": 0, "maxValue": 0, "color": "#000000", "unit": undefined, "icon": undefined});
    const editSeriesAddError = ref('');
    const editSeriesAddErrorValues = ref({});
    const editSeriesSuccess = ref(false);

    const isAuthenticated = computed(() => !!auth.token);

    function getModal() {
      return bootstrap.Modal.getOrCreateInstance(modalEditSeries.value);
    }

    onBeforeUnmount(() => {modal?.dispose()});

    async function getSeries() {
      try {
        loading.value = true;
        error.value = '';
        seriesData.value = await api(
          '/series', {
            method: 'GET',
            auth: true
          });
      } catch (e) {
        error.value = e
      } finally {
        loading.value= false;
      }
    }

    async function addSeries() {
      loading.value = true;
      newSeriesAddError.value = '';
      
      body = {
        "name": newSeriesData.name,
        "minValue": newSeriesData.minValue,
        "maxValue": newSeriesData.maxValue,
        "color": newSeriesData.color,
        "unit": newSeriesData.unit?.trim() || undefined,
        "icon": newSeriesData.icon?.trim() || undefined,
      }

      try {
        const data = await api(
          '/series',
          {method: 'POST', body: {...body}, auth: true}
        );
        newSeriesId.value = data?.id;
      } catch (e) {
        newSeriesAddError.value = e;
        console.log(e.status);
        console.log(e.problem.type);
        console.log(e.problem.title);
        newSeriesAddErrorValues.value = e.errors;
      } finally {
        loading.value = false;
        await getSeries();
      }
    }

    function openEditModal(series) {
      Object.assign(editSeriesData, series);
      getModal().show();
    }

    async function editSeries(id) {
      loading.value = true;
      editSeriesAddError.value = '';
      editSeriesSuccess.value = false;

      body = {
        "name": editSeriesData.name,
        "minValue": editSeriesData.minValue,
        "maxValue": editSeriesData.maxValue,
        "color": editSeriesData.color,
        "unit": editSeriesData.unit?.trim() || undefined,
        "icon": editSeriesData.icon?.trim() || undefined,
      }

      try {
        const data = await api(
          `/series/${id}`,
          {method: 'PUT', body: {...body}, auth: true}
        );
        editSeriesSuccess.value = (data?.id == id);

      } catch (e) {
        editSeriesAddError.value = e;
        console.log(e.status);
        console.log(e.problem.type);
        console.log(e.problem.title);
        editSeriesAddErrorValues.value = e.errors;
      } finally {
        loading.value = false;
        await getSeries();
      }
    }

    function addSeriesFormClear() {
      Object.assign(newSeriesData, {"name": "", "minValue": 0, "maxValue": 0, "color": "#000000", "unit": undefined, "icon": undefined});
      newSeriesAddError.value = '';
      newSeriesId.value = '';
      console.log("cleared");
    }

    function editSeriesFormClear() {
      Object.assign(editSeriesData, {"id": "", "name": "", "minValue": 0, "maxValue": 0, "color": "#000000", "unit": undefined, "icon": undefined});
      editSeriesAddError.value = '';
      editSeriesSuccess.value = false;
      console.log("cleared");
    }

    async function deleteSeries(id) {
      console.log(id);
      try {
        loading.value = true;
        error.value = '';
        _ = await api(
          `/series/${id}`, {
            method: 'DELETE',
            auth: true
          });
        seriesData.value = await api(
          '/series', {
            method: 'GET',
            auth: true
          });
      } catch (e) {
        error.value = e
      } finally {
        loading.value= false;
      }
    }

    

   return { 
    error, response, loading, seriesData, isAuthenticated, modalEditSeries, 
    newSeriesAddError, newSeriesData, newSeriesAddErrorValues, newSeriesId, 
    editSeriesAddError, editSeriesData, editSeriesAddErrorValues, editSeriesSuccess,
    getSeries, addSeries, deleteSeries, addSeriesFormClear, editSeries, editSeriesFormClear, openEditModal
  } 
  }  
};

const app = createApp({
  components: {
    'home': Home,
    'user-login': UserLogin,
    'user-change-password': UserChangePassword,
    'manage-sensors': ManageSensors,
    'manage-series': ManageSeries
  },
  setup() {
    const isAuthenticated = computed(() => !!auth.token);

    const loading = ref(false);
    const saving = ref(false);
    const error = ref('');

    auth.onLogout = () => { state.page = 'home'; };

    onMounted(() => {  });

    return {
      state, isAuthenticated, 
      loading, saving, error,
      auth, logout: () => auth.logout()
    };
  },
})

app.mount('#app');