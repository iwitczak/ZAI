const { createApp, ref, reactive, computed, onMounted } = Vue;

// Page components
const Home = {template: '#tpl-home'};

const UserLogin = {
  template: '#tpl-user-login',
  setup() {
    const credentials = reactive({username: '', password: ''});
    const error = ref('');

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
    return { error, login, credentials };
  }
};

const UserChangePassword = {
  template: '#tpl-user-change-password',
  setup() {
    const passwords = reactive({currentPassword: '', newPassword: ''});
    const error = ref('');

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
    return { error, changePassword, passwords };
  }
};

const ManageSensors = {
  template: '#tpl-manage-sensors',
  setup() {
    
  }
};

const ManageSeries = {
  template: '#tpl-manage-series',
  setup() {
    
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

    // async function loadItems() {
    //   loading.value = true;
    //   error.value = '';
    //   try {
    //     items.value = await api('/sensors');
    //     console.log(items);
    //   } catch (e) {
    //     error.value = e.message;
    //   } finally {
    //     loading.value = false;
    //   }
    // }

    // async function createItem() {
    //   saving.value = true;
    //   try {
    //     items.value.push(await api('/measurements/', { method: 'POST', body: { ...form } }));
    //     form.name = '';
    //   } catch (e) {
    //     error.value = e.message;
    //   } finally {
    //     saving.value = false;
    //   }
    // }

    onMounted(() => {  });

    return {
      state, isAuthenticated, 
      loading, saving, error,
      auth, logout: () => auth.logout()
    };
  },
})

app.mount('#app');