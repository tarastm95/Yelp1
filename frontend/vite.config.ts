import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const API_BASE = env.VITE_API_BASE_URL;
  
  if (!API_BASE) {
    console.error('❌ ERROR: VITE_API_BASE_URL is not set in frontend/.env file!');
    throw new Error('Missing VITE_API_BASE_URL environment variable');
  }
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: API_BASE,
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
