import {fileURLToPath, URL} from 'node:url'

import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        vue(),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        },
    },
    server: {
        port: 8080,
        proxy: {
            "^/(api|static)/": 'http://localhost:8000',
            "^/(ws)/": 'ws://localhost:8000'
        }
    },
    build: {
        assetsDir: 'app',
    },
    base: process.env.NODE_ENV === 'development' ? '/' : '/static/',
})
