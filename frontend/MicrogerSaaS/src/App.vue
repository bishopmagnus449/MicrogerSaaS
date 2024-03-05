<script lang="ts">
import {FontAwesomeIcon} from "@fortawesome/vue-fontawesome";
import * as icons from "@fortawesome/free-solid-svg-icons";
import ReconnectingWebSocket from "reconnecting-websocket";
import axios from "axios";
import _ from 'lodash';


export default {
  components: {FontAwesomeIcon},
  data: () => ({
    showLogs: true,
    writerBusy: false,
    icons: icons,
    serverInfo: {
      host: '',
      port: 22,
      username: 'root',
      password: '',
      github_key: '',
      app: {
        username: 'myadmin',
        password: 'sInner@123s',
        userDomain: '',
        adminDomain: '',
      },
      database: {
        host: 'localhost',
        port: 5432,
        name: 'microger',
        username: 'microger',
        password: 'sInner@123s',
      },
      broker: {
        username: 'django',
        password: 'sInner@123s',
        vhost: 'microger',
      },
    },
    logs: [] as string[],
    config: {
      server: {
        showPassword: false,
      },
      app: {
        showPassword: false,
      },
      database: {
        showPassword: false,
      },
      broker: {
        showPassword: false,
      },
      showDefaultSettings: false,
      finishedDeployment: false,
      showDeploymentInfo: false,
      inProgress: false,
    },
    defaults: {
      database: {
        host: 'localhost',
        port: 5432,
        name: 'microger',
        username: 'microger',
        password: 'sInner@123s',
      },
      broker: {
        username: 'django',
        password: 'sInner@123s',
        vhost: 'microger',
      },
    },
  }),
  methods: {
    async startLoggerWebsocket() {
      const loggerSocket = new ReconnectingWebSocket(`ws://${window.location.host}/ws/logger/`);

      loggerSocket.onopen = async () => {
        this.config.inProgress = false;
        await this.writeLog("Logger WebSocket connection opened.", 'primary')
      };

      loggerSocket.onmessage = async (event) => {
        const data = JSON.parse(event.data)
        await this.writeLog(data.log, data.color)
      };

      loggerSocket.onerror = async () => {
        await this.writeLog("Logger WebSocket connection error", 'danger')
      };

      loggerSocket.onclose = async () => {
        this.config.inProgress = true;
        await this.writeLog("Logger WebSocket connection closed, reconnecting...", 'danger')
      };
    },
    copyToClipboard(text: string, {target}) {
      const input = target.closest('.field').querySelector('.input')
      const button: HTMLButtonElement = target.closest('button')
      const buttonContent = button.innerHTML
      button.classList.add('is-loading')
      try {
        // Modern browsers (Chrome, Firefox, Edge, etc.)
        navigator.clipboard.writeText(text).then(() => {}, (err) => {
          console.error('Failed to copy text:', err);
        });
      } catch (err) {
        // Older browsers (IE11, etc.)
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
          const successful = document.execCommand('copy');
          const msg = successful ? 'Text copied to clipboard: ' + text : 'Failed to copy text.';
          console.log(msg);
        } catch (err) {
          console.error('Failed to copy text:', err);
          return
        }

        document.body.removeChild(textArea);
      }

      setTimeout(() => {
        button.classList.remove('is-loading')
        button.innerHTML = '<span class="is-size-7 is-family-code">Copied!</span>'
        input.classList.add('is-success')
        setTimeout(() => {
          input.classList.remove('is-success')
          button.innerHTML = buttonContent
        }, 300)
      }, 500)
    },
    defaultSettings() {
      this.serverInfo = {
        ...this.serverInfo,
        ..._.cloneDeep(this.defaults),
      }
    },
    async writeLog(log: string, color: 'primary' | 'danger' | 'info' | 'warning' | 'success' | 'grey' = 'grey') {
      while (this.writerBusy) {
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      this.writerBusy = true;
      this.addLog(log)
      const logger = this.$refs.logger
      if (!(logger instanceof HTMLElement)) {
        return
      }
      const child: HTMLSpanElement = document.createElement('span')
      if (color) {
        child.classList.add(`has-text-${color}`)
      }
      logger.appendChild(child);
      child.innerHTML += log
      // for (let l of log.split('')) {
      //   child.innerHTML += l
      //   await new Promise(resolve => setTimeout(resolve, 10))
      //   if (logger.scrollHeight - (logger.scrollTop + logger.clientHeight) <= 100) {
      //     logger.scrollTop = logger.scrollHeight
      //   }
      // }
      logger.innerHTML += '<br>'
      if (logger.scrollHeight - (logger.scrollTop + logger.clientHeight) <= 300) {
        logger.scrollTop = logger.scrollHeight
      }
      this.writerBusy = false;
    },
    addLog(log: string) {
      this.logs = [...this.logs, log];
    },
    submitForm() {
      this.config.inProgress = true;
      axios.post('/api/deploy/', this.serverInfo).then(res => {
        if (res.data.status) {
          this.config.finishedDeployment = true
          this.config.showDeploymentInfo = true
        } else {
          this.writeLog("Deployment failed due to error: " + res.data.error, 'danger')
        }
        this.config.inProgress = false;
      })
      this.config.inProgress = true;
    }
  },
  computed: {
    defaultSettingsChanged() {
      return ['database', 'broker'].some(prop => !_.isEqual((this.serverInfo as any)[prop], (this.defaults as any)[prop]));
    }
  },
  async mounted() {
    await this.writeLog("Welcome to Microger SaaS.", 'primary')
    await this.writeLog("Connecting to logger WebSocket...", 'info')
    const loggerSocket = new ReconnectingWebSocket(`ws://${window.location.host}/ws/logger/`);
    loggerSocket.onopen = async () => {
      await this.writeLog("Logger WebSocket connection opened.", 'primary')
    };
    await this.startLoggerWebsocket()


  },
}
</script>

<template>
  <div class="container p-4 is-flex-grow-1">
    <div class="columns">
      <div class="column customScrollBar vertical h-90">
        <form @submit.prevent="submitForm">
          <div class="field">
            <label class="label">Server IP</label>
            <div class="control">
              <input name="ip" autocomplete="false" required class="input" v-model="serverInfo.host" type="text"
                     placeholder="Server IP">
            </div>
          </div>
          <div class="field">
            <label class="label">Server Port</label>
            <div class="control">
              <input autocomplete="false" required class="input" v-model="serverInfo.port" type="number"
                     placeholder="Server Port">
            </div>
          </div>
          <div class="field">
            <label class="label">Username</label>
            <div class="control">
              <input required class="input" v-model="serverInfo.username" type="text" placeholder="Username">
            </div>
          </div>
          <label class="label">Password
            </label>
          <div class="field has-addons">

            <div class="control is-flex is-flex-grow-1">
              <input required class="input" v-model="serverInfo.password"
                     :type="config.server.showPassword?'text':'password'"
                     placeholder="Password">
            </div>
            <div class="control">
              <button class="button" type="button" @click="config.server.showPassword = !config.server.showPassword">
                <font-awesome-icon :icon="config.server.showPassword ? icons.faEye : icons.faEyeSlash"/>
              </button>
            </div>
            <p class="help is-danger is-hidden">This email is invalid</p>
          </div>
          <div class="field">
            <label class="label">Github Key</label>
            <div class="control">
              <input required class="input" v-model="serverInfo.github_key" type="text" placeholder="Github Key">
            </div>
          </div>
          <div>
            <header class="card-header is-align-items-center">
              <p class="card-header-title">
                Deployment Options
              </p>
              <button type="button" class="button is-rounded is-link p-3"
                      title="Change default settings" @click="config.showDefaultSettings = !config.showDefaultSettings">
                <font-awesome-icon :icon="icons.faSliders"/>
              </button>
            </header>
            <div>
              <div class="card-content">
                <div class="field">
                  <label class="label">User Domain</label>
                  <div class="control">
                    <input required class="input" v-model="serverInfo.app.userDomain" type="text"
                           placeholder="User Domain; e.g. example.com">
                  </div>
                </div>
                <div class="field">
                  <label class="label">Admin Domain</label>
                  <div class="control">
                    <input required class="input" v-model="serverInfo.app.adminDomain" type="text"
                           placeholder="Admin Domain; e.g. example.com">
                  </div>
                </div>
                <div class="field">
                  <label class="label">Username</label>
                  <div class="control">
                    <input required class="input" v-model="serverInfo.app.username" type="text" placeholder="Username">
                  </div>
                </div>
                <label class="label">Password</label>
                <div class="field has-addons">
                  <div class="control is-flex is-flex-grow-1">
                    <input required class="input" v-model="serverInfo.app.password"
                           :type="config.app.showPassword?'text':'password'"
                           placeholder="Password">
                  </div>
                  <div class="control">
                    <button class="button" type="button" @click="config.app.showPassword = !config.app.showPassword">
                      <font-awesome-icon :icon="config.app.showPassword ? icons.faEye : icons.faEyeSlash" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="field is-grouped is-justify-content-center">
            <div class="control">
              <button v-if="config.finishedDeployment" type="button" class="button is-link"
                      @click="config.showDeploymentInfo = true">Deployment Info
              </button>
              <button v-else type="submit" class="button is-link" :class="{'is-loading': config.inProgress}" :disabled="config.inProgress">Deploy</button>
            </div>
          </div>
        </form>
      </div>
      <div class="column is-flex-grow-1 is-flex">
        <div class="has-background-light box is-flex-grow-1 is-flex logger-container">
          <div ref="logger" id="logger" class="customScrollBar vertical is-flex-grow-1"></div>
        </div>
      </div>
    </div>
    <div class="modal" :class="{'is-active': config.showDeploymentInfo}">
      <div class="modal-background is-clickable"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Deployment Finished</p>
          <button class="delete" aria-label="close" @click="config.showDeploymentInfo = false"></button>
        </header>
        <section class="modal-card-body">
          <label class="label">Django admin panel</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <span class="input has-text-grey">https://{{serverInfo.app.adminDomain}}/</span>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.adminDomain}/`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Microger panel</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <span class="input has-text-grey">https://{{serverInfo.app.adminDomain}}/panel</span>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.adminDomain}/panel`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Username</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{serverInfo.app.username}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(serverInfo.app.username, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Password</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{serverInfo.app.password}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(serverInfo.app.password, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Office Login</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{`https://${serverInfo.app.userDomain}/accounts/callbacks/office/`}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.userDomain}/accounts/callbacks/office/`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Office Callback</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{`https://${serverInfo.app.userDomain}/accounts/signin/office/`}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.userDomain}/accounts/signin/office/`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Gmail Login</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{`https://${serverInfo.app.userDomain}/accounts/callbacks/google/`}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.userDomain}/accounts/callbacks/google/`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
          <label class="label">Gmail Callback</label>
          <div class="field has-addons">
            <div class="control is-flex-grow-1">
              <pre class="input has-text-grey">{{`https://${serverInfo.app.userDomain}/accounts/signin/google/`}}</pre>
            </div>
            <div class="control">
              <button class="button" @click="copyToClipboard(`https://${serverInfo.app.userDomain}/accounts/signin/google/`, $event)">
                <font-awesome-icon :icon="icons.faCopy"/>
              </button>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <a :href="`https://${serverInfo.app.adminDomain}/panel`" target="_blank" class="button is-link">Redirect To
            Login Panel</a>
        </footer>
      </div>
    </div>
    <div class="modal" :class="{'is-active': config.showDefaultSettings}">
      <div class="modal-background is-clickable"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Default Settings</p>
          <!--          <button class="delete" aria-label="close" @click="config.showDefaultSettings = false"></button>-->
        </header>

        <section class="modal-card-body">
          <form id="default-settings-form" @submit.prevent="config.showDefaultSettings = false">
            <div>
              <header class="card-header">
                <p class="card-header-title">
                  Database Settings
                </p>
              </header>
              <div>
                <div class="card-content">
                  <div class="field">
                    <label class="label">Host</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.database.host" type="text" disabled
                             placeholder="Host">
                    </div>
                  </div>
                  <div class="field">
                    <label class="label">Port</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.database.port" type="number" disabled
                             placeholder="Port">
                    </div>
                  </div>
                  <div class="field">
                    <label class="label">Database Name</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.database.name" type="text"
                             placeholder="Database Name">
                    </div>
                  </div>
                  <div class="field">
                    <label class="label">Username</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.database.username" type="text"
                             placeholder="Username">
                    </div>
                  </div>
                  <label class="label">Password</label>
                  <div class="field has-addons">
                    <div class="control is-flex is-flex-grow-1">
                      <input required class="input" v-model="serverInfo.database.password"
                             :type="config.database.showPassword?'text':'password'"
                             placeholder="Password">
                    </div>
                    <div class="control">
                      <button class="button" type="button" @click="config.database.showPassword = !config.database.showPassword">
                        <font-awesome-icon :icon="config.database.showPassword ? icons.faEye : icons.faEyeSlash" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div>
              <header class="card-header">
                <p class="card-header-title">
                  Broker Settings
                </p>
              </header>
              <div>
                <div class="card-content">
                  <div class="field">
                    <label class="label">VHost</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.broker.vhost" type="text" placeholder="VHost">
                    </div>
                  </div>
                  <div class="field">
                    <label class="label">Username</label>
                    <div class="control">
                      <input required class="input" v-model="serverInfo.broker.username" type="text"
                             placeholder="Username">
                    </div>
                  </div>
                  <label class="label">Password</label>
                  <div class="field has-addons">
                    <div class="control is-flex is-flex-grow-1">
                      <input required class="input" v-model="serverInfo.broker.password"
                             :type="config.broker.showPassword?'text':'password'"
                             placeholder="Password">
                    </div>
                    <div class="control">
                      <button class="button" type="button" @click="config.broker.showPassword = !config.broker.showPassword">
                        <font-awesome-icon :icon="config.broker.showPassword ? icons.faEye : icons.faEyeSlash" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </form>
        </section>
        <footer class="modal-card-foot">
          <button class="button is-link" type="submit" form="default-settings-form">{{ defaultSettingsChanged ? 'Keep changes' : 'Close' }}
          </button>
          <button class="button" title="Reset to default values" @click="defaultSettings()">Defaults</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>

div#logger {
  min-height: 340px;
  font-family: monospace;

  &::after {
    content: "\25AE";
    animation: blink 1.3s infinite;
  }
}

@keyframes blink {
  0%, 50%, 100% {
    opacity: 1;
  }
  25%, 75% {
    opacity: 0;
  }
}
</style>
<style>
.is-borderless {
  border: 0 !important;
}

.h-90 {
  min-height: 90vh;
}

/* Use the attribute selector to apply the color style */
span[data-type="danger"] {
  color: #5178a4;
}

span[data-type="success"] {
  color: #03a44e;
}

span[data-type="info"] {
  color: #5178a4;
}
</style>