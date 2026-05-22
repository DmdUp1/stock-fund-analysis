import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/stocks',
    },
    {
      path: '/stocks',
      name: 'stocks',
      component: () => import('@/views/StockAnalysisView.vue'),
    },
    {
      path: '/funds',
      name: 'funds',
      component: () => import('@/views/FundAnalysisView.vue'),
    },
    {
      path: '/portfolio/stocks',
      name: 'portfolio-stocks',
      component: () => import('@/views/StockPortfolioView.vue'),
    },
    {
      path: '/portfolio/funds',
      name: 'portfolio-funds',
      component: () => import('@/views/FundPortfolioView.vue'),
    },
    {
      path: '/warehouse',
      name: 'warehouse',
      component: () => import('@/views/WarehouseView.vue'),
    },
    {
      path: '/warehouse/:code',
      name: 'warehouse-detail',
      component: () => import('@/views/WarehouseDetailView.vue'),
    },
  ],
})

export default router
