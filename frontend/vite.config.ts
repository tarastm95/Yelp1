import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  if (!env.VITE_API_BASE_URL) {
    throw new Error('❌ VITE_API_BASE_URL must be set in frontend/.env file!');
  }
  
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
          target: env.VITE_API_BASE_URL,
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
