import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0', // Дозволяє доступ з Docker контейнера
      port: 5173,
      watch: {
        usePolling: true, // Для стабільної роботи в Docker на Windows
      },
      proxy: {
        '/api': {
          target: process.env.NODE_ENV === 'development' && process.env.DOCKER_ENV 
            ? 'http://backend:8000' // Для Docker контейнера
            : env.VITE_API_BASE_URL || 'http://localhost:8000', // Для локальної розробки
          changeOrigin: true,
        },
        '/yelp-api': {
          target: 'https://api.yelp.com',
          changeOrigin: true,
          rewrite: path => path.replace(/^\/yelp-api/, '/v3'),
        },
      },
    },
  };
});
