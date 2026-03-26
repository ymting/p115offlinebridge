<template>
  <v-card class="mx-auto" max-width="1100" rounded="lg" variant="elevated">
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-link-variant" class="mr-2" color="primary" />
      115离线桥接配置
    </v-card-title>
    <v-divider />
    <v-card-text class="py-4">
      <v-alert
        v-if="message.text"
        :type="message.type"
        density="compact"
        variant="tonal"
        class="mb-4"
      >
        {{ message.text }}
      </v-alert>

      <v-row>
        <v-col cols="12" md="3">
          <v-switch v-model="config.enabled" label="启用插件" color="success" />
        </v-col>
        <v-col cols="12" md="3">
          <v-switch v-model="config.notify" label="发送系统通知" color="success" />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="config.adapter"
            label="默认接口对象（切换即生效）"
            :items="adapterOptions"
            item-title="title"
            item-value="value"
            density="comfortable"
            variant="outlined"
            :loading="adapterSwitching"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.moviepilot_url"
            label="MoviePilot 地址"
            hint="仅按此地址调用 P115StrmHelper（不再自动回退默认地址）"
            persistent-hint
            density="comfortable"
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.moviepilot_api_token"
            label="MoviePilot API Token"
            :type="showApiToken ? 'text' : 'password'"
            hint="留空时默认使用系统 API Token"
            persistent-hint
            density="comfortable"
            variant="outlined"
          >
            <template #append-inner>
              <v-icon
                :icon="showApiToken ? 'mdi-eye-off' : 'mdi-eye'"
                @click="showApiToken = !showApiToken"
              />
            </template>
          </v-text-field>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="8">
          <v-text-field
            v-model="config.p115_target_path"
            label="P115 固定目标目录"
            hint="点击右侧按钮浏览 115 目录并自动回填"
            persistent-hint
            density="comfortable"
            variant="outlined"
          >
            <template #append>
              <v-btn
                variant="tonal"
                color="primary"
                prepend-icon="mdi-folder-search"
                :loading="dirDialog.loading && dirDialog.provider === 'p115'"
                @click="openDirSelector('p115')"
              >
                选择115目录
              </v-btn>
            </template>
          </v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model.number="config.request_timeout"
            label="请求超时（秒）"
            type="number"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-divider class="my-3" />

      <v-row>
        <v-col cols="12" md="3">
          <v-text-field
            v-model="config.cd2_host"
            label="CloudDrive2 Host"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-text-field
            v-model.number="config.cd2_port"
            label="CloudDrive2 Port"
            type="number"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-text-field
            v-model="config.cd2_username"
            label="CloudDrive2 用户名"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
        <v-col cols="12" md="3">
          <v-text-field
            v-model="config.cd2_password"
            :type="showCd2Password ? 'text' : 'password'"
            label="CloudDrive2 密码"
            density="comfortable"
            variant="outlined"
          >
            <template #append-inner>
              <v-icon
                :icon="showCd2Password ? 'mdi-eye-off' : 'mdi-eye'"
                @click="showCd2Password = !showCd2Password"
              />
            </template>
          </v-text-field>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="8">
          <v-text-field
            v-model="config.cd2_target_path"
            label="CloudDrive2 默认目标目录"
            hint="点击右侧按钮浏览 CloudDrive2 目录并自动回填"
            persistent-hint
            density="comfortable"
            variant="outlined"
          >
            <template #append>
              <v-btn
                variant="tonal"
                color="primary"
                prepend-icon="mdi-folder-network"
                :loading="dirDialog.loading && dirDialog.provider === 'cd2'"
                @click="openDirSelector('cd2')"
              >
                选择CD2目录
              </v-btn>
            </template>
          </v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model.number="config.cd2_check_after_secs"
            label="CD2 检查延迟（秒）"
            type="number"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="4">
          <v-switch
            v-model="config.auto_recognize_enabled"
            label="自动识别用户消息"
            color="success"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-switch
            v-model="config.auto_recognize_share_enabled"
            label="自动识别115分享链接"
            color="success"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-switch
            v-model="config.auto_recognize_allow_http_torrent"
            label="自动识别 .torrent 链接"
            color="success"
          />
        </v-col>
      </v-row>
    </v-card-text>
    <v-divider />
    <v-card-actions class="px-4 py-3">
      <v-btn variant="text" color="default" prepend-icon="mdi-arrow-left" @click="emit('switch')">
        返回
      </v-btn>
      <v-spacer />
      <v-btn
        color="primary"
        variant="elevated"
        prepend-icon="mdi-content-save"
        :loading="saveLoading"
        @click="saveConfig"
      >
        保存配置
      </v-btn>
    </v-card-actions>
  </v-card>

  <v-dialog v-model="dirDialog.show" max-width="760">
    <v-card rounded="lg">
      <v-card-title class="d-flex align-center">
        <v-icon
          :icon="dirDialog.provider === 'cd2' ? 'mdi-folder-network' : 'mdi-folder-search'"
          class="mr-2"
          color="primary"
        />
        {{ dirDialog.provider === "cd2" ? "选择CloudDrive2目录" : "选择115目录" }}
      </v-card-title>
      <v-divider />
      <v-card-text class="py-3">
        <v-text-field
          v-model="dirDialog.currentPath"
          label="当前路径"
          variant="outlined"
          density="comfortable"
          @keyup.enter="loadDirContent"
        >
          <template #append-inner>
            <v-icon icon="mdi-refresh" @click="loadDirContent" />
          </template>
        </v-text-field>

        <v-alert v-if="dirDialog.error" type="error" density="compact" class="mb-2" variant="tonal">
          {{ dirDialog.error }}
        </v-alert>

        <v-progress-linear v-if="dirDialog.loading" color="primary" indeterminate class="mb-2" />

        <v-list border rounded max-height="360" class="overflow-y-auto">
          <v-list-item
            v-if="dirDialog.currentPath !== '/'"
            prepend-icon="mdi-arrow-up-bold-circle-outline"
            title="返回上级目录"
            @click="navigateToParent"
          />
          <v-list-item
            v-for="item in dirDialog.items"
            :key="item.path"
            prepend-icon="mdi-folder"
            :title="item.path"
            @click="selectDir(item)"
          />
          <v-list-item v-if="!dirDialog.loading && !dirDialog.items.length" title="该目录下无子目录" />
        </v-list>
      </v-card-text>
      <v-divider />
      <v-card-actions class="px-4 py-3">
        <v-spacer />
        <v-btn variant="text" @click="closeDirDialog">取消</v-btn>
        <v-btn color="primary" variant="elevated" @click="confirmDirSelection">选择当前目录</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { reactive, ref, watch } from "vue";

const PLUGIN_ID = "P115OfflineBridge";

const props = defineProps({
  api: {
    type: [Object, Function],
    required: true,
  },
  initialConfig: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["save", "switch"]);

const adapterOptions = [
  { title: "P115StrmHelper API（推荐）", value: "p115_strmhelper" },
  { title: "CloudDrive2 gRPC", value: "clouddrive2_grpc" },
];

function createDefaultModel() {
  return {
    enabled: false,
    notify: true,
    adapter: "p115_strmhelper",
    moviepilot_url: "",
    moviepilot_api_token: "",
    request_timeout: 20,
    p115_target_path: "",
    auto_recognize_enabled: true,
    auto_recognize_share_enabled: true,
    auto_recognize_allow_http_torrent: true,
    cd2_host: "localhost",
    cd2_port: 19798,
    cd2_username: "",
    cd2_password: "",
    cd2_target_path: "/",
    cd2_check_after_secs: 10,
  };
}

const config = reactive(createDefaultModel());
const showApiToken = ref(false);
const showCd2Password = ref(false);
const saveLoading = ref(false);
const adapterSwitching = ref(false);
const adapterWatchReady = ref(false);
const suppressAdapterWatch = ref(false);

const message = reactive({
  text: "",
  type: "info",
});

const dirDialog = reactive({
  show: false,
  loading: false,
  error: "",
  currentPath: "/",
  items: [],
  provider: "p115",
});

watch(
  () => props.initialConfig,
  (val) => {
    Object.assign(config, createDefaultModel(), val || {});
    adapterWatchReady.value = true;
  },
  { immediate: true }
);

watch(
  () => config.adapter,
  async (next, prev) => {
    if (!adapterWatchReady.value || suppressAdapterWatch.value) {
      return;
    }
    if (!prev || next === prev) {
      return;
    }
    await applyAdapterImmediately(next, prev);
  }
);

function showMessage(text, type = "info") {
  message.text = text;
  message.type = type;
  setTimeout(() => {
    if (message.text === text) {
      message.text = "";
    }
  }, 3500);
}

function normalizePath(path) {
  let value = String(path || "").trim().replace(/\\/g, "/");
  if (!value) return "";
  if (!value.startsWith("/")) value = `/${value}`;
  if (value.length > 1 && value.endsWith("/")) value = value.slice(0, -1);
  return value || "/";
}

function toInt(value, fallback) {
  const n = Number(value);
  if (Number.isFinite(n)) {
    return Math.trunc(n);
  }
  return fallback;
}

async function applyAdapterImmediately(next, prev) {
  adapterSwitching.value = true;
  try {
    const result = await props.api.post(
      `plugin/${PLUGIN_ID}/set_adapter?adapter=${encodeURIComponent(next)}`,
      {}
    );
    if (!result || result.code !== 0) {
      throw new Error(result?.msg || "切换失败");
    }
    showMessage(`接口对象已即时切换为：${next}`, "success");
  } catch (error) {
    showMessage(`切换接口对象失败：${error?.message || "未知错误"}`, "error");
    suppressAdapterWatch.value = true;
    config.adapter = prev;
    suppressAdapterWatch.value = false;
  } finally {
    adapterSwitching.value = false;
  }
}

async function saveConfig() {
  saveLoading.value = true;
  try {
    const payload = JSON.parse(JSON.stringify(config));
    payload.request_timeout = Math.max(toInt(payload.request_timeout, 20), 1);
    payload.cd2_port = Math.max(toInt(payload.cd2_port, 19798), 1);
    payload.cd2_check_after_secs = Math.max(toInt(payload.cd2_check_after_secs, 10), 0);
    payload.p115_target_path = normalizePath(payload.p115_target_path);
    payload.cd2_target_path = normalizePath(payload.cd2_target_path) || "/";
    emit("save", payload);
    showMessage("配置已提交保存。", "success");
  } catch (error) {
    showMessage(`保存配置失败: ${error?.message || "未知错误"}`, "error");
  } finally {
    saveLoading.value = false;
  }
}

function openDirSelector(provider) {
  dirDialog.provider = provider;
  dirDialog.show = true;
  dirDialog.error = "";
  dirDialog.items = [];
  if (provider === "cd2") {
    dirDialog.currentPath = normalizePath(config.cd2_target_path) || "/";
  } else {
    dirDialog.currentPath = normalizePath(config.p115_target_path) || "/";
  }
  loadDirContent();
}

function closeDirDialog() {
  dirDialog.show = false;
  dirDialog.loading = false;
  dirDialog.error = "";
  dirDialog.items = [];
}

function navigateToParent() {
  if (dirDialog.currentPath === "/") return;
  const current = normalizePath(dirDialog.currentPath);
  const parent = current.substring(0, current.lastIndexOf("/"));
  dirDialog.currentPath = parent || "/";
  loadDirContent();
}

function selectDir(item) {
  if (!item?.is_dir) return;
  dirDialog.currentPath = normalizePath(item.path) || "/";
  loadDirContent();
}

function confirmDirSelection() {
  const selected = normalizePath(dirDialog.currentPath) || "/";
  if (dirDialog.provider === "cd2") {
    config.cd2_target_path = selected;
    showMessage(`已回填 CloudDrive2 目录: ${selected}`, "success");
  } else {
    config.p115_target_path = selected;
    showMessage(`已回填 115 目录: ${selected}`, "success");
  }
  closeDirDialog();
}

async function loadDirContent() {
  dirDialog.loading = true;
  dirDialog.error = "";
  dirDialog.items = [];
  try {
    const path = normalizePath(dirDialog.currentPath) || "/";
    const apiPath =
      dirDialog.provider === "cd2"
        ? `plugin/${PLUGIN_ID}/browse_cd2_dir?path=${encodeURIComponent(path)}`
        : `plugin/${PLUGIN_ID}/browse_dir?path=${encodeURIComponent(path)}&is_local=false`;
    const result = await props.api.get(apiPath);
    if (!result || result.code !== 0 || !result.data) {
      throw new Error(result?.msg || "目录加载失败");
    }
    dirDialog.currentPath = normalizePath(result.data.path) || "/";
    dirDialog.items = Array.isArray(result.data.items)
      ? result.data.items
          .filter((item) => item && item.is_dir)
          .sort((a, b) => String(a.path || "").localeCompare(String(b.path || "")))
      : [];
  } catch (error) {
    dirDialog.error = error?.message || "目录加载失败";
  } finally {
    dirDialog.loading = false;
  }
}
</script>
