import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import federation from "@originjs/vite-plugin-federation";

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: "115offlinebridge",
      filename: "remoteEntry.js",
      exposes: {
        "./Config": "./src/components/Config.vue",
        "./Page": "./src/components/Page.vue",
        "./Dashboard": "./src/components/Dashboard.vue",
      },
      shared: {
        vue: {
          requiredVersion: false,
          generate: false,
        },
        vuetify: {
          requiredVersion: false,
          generate: false,
          singleton: true,
        },
        "vuetify/styles": {
          requiredVersion: false,
          generate: false,
          singleton: true,
        },
      },
      format: "esm",
    }),
  ],
  build: {
    target: "esnext",
    outDir: "../../plugins.v2/p115offlinebridge/dist",
    emptyOutDir: true,
    cssCodeSplit: true,
  },
  server: {
    port: 5013,
    cors: true,
  },
});
