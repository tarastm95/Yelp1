// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Get backend URL from environment variable
  const DEV_API_URL = process.env.REACT_APP_DEV_API_URL;
  if (!DEV_API_URL) {
    console.error('❌ ERROR: REACT_APP_DEV_API_URL is not set in frontend/.env file!');
    throw new Error('Missing REACT_APP_DEV_API_URL environment variable');
  }

  // 1) Проксі для вашого Django-бекенду
  app.use(
    '/api',
    createProxyMiddleware({
      target: DEV_API_URL,
      changeOrigin: true,
    })
  );

  // 2) (тільки для деву!) Проксі напряму до Yelp API
  app.use(
    '/yelp-api',
    createProxyMiddleware({
      target: 'https://api.yelp.com',
      changeOrigin: true,
      pathRewrite: { '^/yelp-api': '/v3' },
    })
  );
};
