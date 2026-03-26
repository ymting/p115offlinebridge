<template>
  <v-app>
    <v-container class="py-4">
      <v-tabs v-model="tab" class="mb-4">
        <v-tab value="page">页面</v-tab>
        <v-tab value="config">配置</v-tab>
      </v-tabs>
      <v-window v-model="tab">
        <v-window-item value="page">
          <Page :api="mockApi" :initial-config="mockConfig" @switch="tab = 'config'" />
        </v-window-item>
        <v-window-item value="config">
          <Config
            :api="mockApi"
            :initial-config="mockConfig"
            @switch="tab = 'page'"
            @save="handleSave"
          />
        </v-window-item>
      </v-window>
    </v-container>
  </v-app>
</template>

<script setup>
import { ref } from "vue";
import Config from "./components/Config.vue";
import Page from "./components/Page.vue";

const tab = ref("config");

const mockConfig = {
  enabled: true,
  notify: true,
  adapter: "p115_strmhelper",
  moviepilot_url: "http://127.0.0.1:3000",
  moviepilot_api_token: "",
  request_timeout: 20,
  p115_target_path: "/电影",
  p115_path_select_mode: "fixed",
  p115_target_paths: "/电影/剧集\n/电影/电影",
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

const mockApi = {
  async get() {
    return { code: 0, msg: "ok", data: { path: "/", items: [] } };
  },
};

function handleSave(config) {
  // local dev only
  // eslint-disable-next-line no-console
  console.log("save payload", config);
}
</script>
