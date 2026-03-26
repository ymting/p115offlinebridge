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
            label="默认接口对象"
            :items="adapterOptions"
            item-title="title"
            item-value="value"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="config.moviepilot_url"
            label="MoviePilot 地址"
            hint="用于调用 P115StrmHelper 插件 API"
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
        <v-col cols="12" md="7">
          <v-text-field
            v-model="config.p115_target_path"
            label="P115 默认目标目录"
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
                :loading="dirDialog.loading && dirDialog.target === 'default'"
                @click="openDirSelector('default')"
              >
                选择115目录
              </v-btn>
            </template>
          </v-text-field>
        </v-col>
        <v-col cols="12" md="5">
          <v-text-field
            v-model.number="config.request_timeout"
            label="请求超时（秒）"
            type="number"
            density="comfortable"
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="config.p115_path_select_mode"
            label="P115 目录选择模式"
            :items="pathModeOptions"
            item-title="title"
            item-value="value"
            density="comfortable"
            variant="outlined"
            hint="固定目录使用上方默认目录；轮询/随机使用多目录列表"
            persistent-hint
          />
        </v-col>
        <v-col cols="12" md="8">
          <v-textarea
            v-model="config.p115_target_paths"
            label="P115 多目录列表（每行一个）"
            rows="4"
            auto-grow
            density="comfortable"
            variant="outlined"
            hint="可点击右侧按钮选择目录并自动追加"
            persistent-hint
          >
            <template #append>
              <v-btn
                variant="tonal"
                color="primary"
                prepend-icon="mdi-folder-multiple"
                :loading="dirDialog.loading && dirDialog.target === 'multi'"
                @click="openDirSelector('multi')"
              >
                添加目录
              </v-btn>
            </template>
          </v-textarea>
          <div class="d-flex flex-wrap ga-2 mt-2">
            <v-chip
              v-for="(item, index) in multiPathItems"
              :key="item"
              closable
              size="small"
              color="primary"
              variant="tonal"
              @click:close="removeMultiPath(index)"
            >
              {{ item }}
            </v-chip>
          </div>
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
            hint="仅在 CloudDrive2 接口对象下生效"
            persistent-hint
            density="comfortable"
            variant="outlined"
          />
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
        <v-icon icon="mdi-folder-search" class="mr-2" color="primary" />
        选择115目录
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
            :title="item.name"
            :subtitle="item.path"
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
import { computed, reactive, ref, watch } from "vue";

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

const pathModeOptions = [
  { title: "固定目录", value: "fixed" },
  { title: "多目录轮询", value: "round_robin" },
  { title: "多目录随机", value: "random" },
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
    p115_path_select_mode: "fixed",
    p115_target_paths: "",
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
  target: "default",
});

watch(
  () => props.initialConfig,
  (val) => {
    Object.assign(config, createDefaultModel(), val || {});
  },
  { immediate: true }
);

const multiPathItems = computed(() => parsePathLines(config.p115_target_paths));

function showMessage(text, type = "info") {
  message.text = text;
  message.type = type;
  setTimeout(() => {
    if (message.text === text) {
      message.text = "";
    }
  }, 3500);
}

function parsePathLines(text) {
  if (!text) return [];
  const lines = String(text)
    .replace(/\r/g, "\n")
    .replace(/，/g, ",")
    .replace(/；/g, ";")
    .replace(/;/g, ",")
    .split("\n")
    .flatMap((line) => line.split(","))
    .map((line) => normalizePath(line))
    .filter(Boolean);
  const deduped = [];
  const seen = new Set();
  for (const item of lines) {
    if (!seen.has(item)) {
      seen.add(item);
      deduped.push(item);
    }
  }
  return deduped;
}

function normalizePath(path) {
  let value = String(path || "").trim().replace(/\\/g, "/");
  if (!value) return "";
  if (!value.startsWith("/")) value = `/${value}`;
  if (value.length > 1 && value.endsWith("/")) value = value.slice(0, -1);
  return value || "/";
}

function removeMultiPath(index) {
  const items = [...multiPathItems.value];
  items.splice(index, 1);
  config.p115_target_paths = items.join("\n");
}

function toInt(value, fallback) {
  const n = Number(value);
  if (Number.isFinite(n)) {
    return Math.trunc(n);
  }
  return fallback;
}

async function saveConfig() {
  saveLoading.value = true;
  try {
    const payload = JSON.parse(JSON.stringify(config));
    payload.request_timeout = Math.max(toInt(payload.request_timeout, 20), 1);
    payload.cd2_port = Math.max(toInt(payload.cd2_port, 19798), 1);
    payload.cd2_check_after_secs = Math.max(toInt(payload.cd2_check_after_secs, 10), 0);
    payload.p115_target_path = normalizePath(payload.p115_target_path);
    payload.p115_target_paths = parsePathLines(payload.p115_target_paths).join("\n");
    payload.cd2_target_path = payload.cd2_target_path || "/";
    emit("save", payload);
    showMessage("配置已提交保存。", "success");
  } catch (error) {
    showMessage(`保存配置失败: ${error?.message || "未知错误"}`, "error");
  } finally {
    saveLoading.value = false;
  }
}

function openDirSelector(target) {
  dirDialog.target = target;
  dirDialog.show = true;
  dirDialog.error = "";
  dirDialog.items = [];
  if (target === "default" && config.p115_target_path) {
    dirDialog.currentPath = normalizePath(config.p115_target_path) || "/";
  } else {
    dirDialog.currentPath = "/";
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
  if (dirDialog.target === "default") {
    config.p115_target_path = selected;
    showMessage(`已回填默认目录: ${selected}`, "success");
  } else {
    const items = parsePathLines(config.p115_target_paths);
    if (items.includes(selected)) {
      showMessage("多目录列表中已存在该目录。", "warning");
    } else {
      items.push(selected);
      config.p115_target_paths = items.join("\n");
      showMessage(`已添加目录: ${selected}`, "success");
    }
  }
  closeDirDialog();
}

async function loadDirContent() {
  dirDialog.loading = true;
  dirDialog.error = "";
  dirDialog.items = [];
  try {
    const path = normalizePath(dirDialog.currentPath) || "/";
    const apiPath = `plugin/${PLUGIN_ID}/browse_dir?path=${encodeURIComponent(path)}&is_local=false`;
    const result = await props.api.get(apiPath);
    if (!result || result.code !== 0 || !result.data) {
      throw new Error(result?.msg || "目录加载失败");
    }
    dirDialog.currentPath = normalizePath(result.data.path) || "/";
    dirDialog.items = Array.isArray(result.data.items)
      ? result.data.items
          .filter((item) => item && item.is_dir)
          .sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")))
      : [];
  } catch (error) {
    dirDialog.error = error?.message || "目录加载失败";
  } finally {
    dirDialog.loading = false;
  }
}
</script>
