// src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://46.62.139.177:8000';
  // 1) Proxy to your Django backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: API_BASE,
      changeOrigin: true,
    })
  );

  // 2) (dev only!) Proxy directly to the Yelp API
  app.use(
    '/yelp-api',
    createProxyMiddleware({
      target: 'https://api.yelp.com',
      changeOrigin: true,
      pathRewrite: { '^/yelp-api': '/v3' },
    })
  );
};
