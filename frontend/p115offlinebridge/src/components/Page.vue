<template>
  <v-card class="mx-auto" max-width="1100" rounded="lg" variant="elevated">
    <v-card-title class="d-flex align-center">
      <v-icon icon="mdi-cloud-download-outline" class="mr-2" color="primary" />
      115离线桥接
    </v-card-title>
    <v-divider />
    <v-card-text class="py-4">
      <v-alert
        v-if="state.error"
        type="error"
        density="compact"
        variant="tonal"
        class="mb-4"
      >
        {{ state.error }}
      </v-alert>
      <v-row>
        <v-col cols="12" md="4">
          <v-sheet border rounded class="pa-4 h-100">
            <div class="text-caption text-medium-emphasis">插件状态</div>
            <div class="text-h6 mt-2">
              <v-chip :color="state.enabled ? 'success' : 'default'" variant="tonal">
                {{ state.enabled ? "已启用" : "已禁用" }}
              </v-chip>
            </div>
          </v-sheet>
        </v-col>
        <v-col cols="12" md="4">
          <v-sheet border rounded class="pa-4 h-100">
            <div class="text-caption text-medium-emphasis">接口对象</div>
            <div class="text-h6 mt-2">{{ state.adapter || "-" }}</div>
          </v-sheet>
        </v-col>
        <v-col cols="12" md="4">
          <v-sheet border rounded class="pa-4 h-100">
            <div class="text-caption text-medium-emphasis">P115 默认目录</div>
            <div class="text-body-1 mt-2">{{ state.p115_target_path || "-" }}</div>
          </v-sheet>
        </v-col>
      </v-row>

      <v-row class="mt-2">
        <v-col cols="12">
          <v-sheet border rounded class="pa-4">
            <div class="text-subtitle-2 mb-2">说明</div>
            <div class="text-body-2 text-medium-emphasis">
              该插件会调用 P115StrmHelper 提交离线下载任务。配置页支持“选择115目录”按钮，
              可浏览目录树并自动回填到默认目录或多目录列表。
            </div>
          </v-sheet>
        </v-col>
      </v-row>
    </v-card-text>
    <v-divider />
    <v-card-actions class="px-4 py-3">
      <v-btn color="primary" variant="elevated" prepend-icon="mdi-cog" @click="emit('switch')">
        打开配置
      </v-btn>
      <v-spacer />
      <v-btn
        color="default"
        variant="text"
        prepend-icon="mdi-refresh"
        :loading="state.loading"
        @click="loadStatus"
      >
        刷新状态
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { onMounted, reactive } from "vue";

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

const emit = defineEmits(["switch", "close"]);

const state = reactive({
  loading: false,
  error: "",
  enabled: !!props.initialConfig?.enabled,
  adapter: props.initialConfig?.adapter || "",
  p115_target_path: props.initialConfig?.p115_target_path || "",
});

async function loadStatus() {
  state.loading = true;
  state.error = "";
  try {
    const result = await props.api.get(`plugin/${PLUGIN_ID}/status`);
    if (!result || result.code !== 0 || !result.data) {
      throw new Error(result?.msg || "状态获取失败");
    }
    state.enabled = !!result.data.enabled;
    state.adapter = result.data.adapter || "";
    state.p115_target_path = result.data.p115_target_path || "";
  } catch (error) {
    state.error = error?.message || "状态获取失败";
  } finally {
    state.loading = false;
  }
}

onMounted(() => {
  loadStatus();
});
</script>
