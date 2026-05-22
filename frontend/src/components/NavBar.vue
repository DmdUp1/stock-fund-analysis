<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const links = [
  { path: '/stocks', label: '股票分析', icon: '📊' },
  { path: '/funds', label: '基金分析', icon: '📦' },
  { path: '/portfolio/stocks', label: '股票持仓', icon: '📈' },
  { path: '/portfolio/funds', label: '基金持仓', icon: '📁' },
  { path: '/warehouse', label: '分析仓库', icon: '🗄️' },
]
</script>

<template>
  <nav class="navbar">
    <div class="nav-inner">
      <router-link to="/" class="logo">金融分析</router-link>
      <div class="nav-links">
        <router-link
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          class="nav-link"
          :class="{ active: route.path === link.path }"
        >
          <span class="nav-icon">{{ link.icon }}</span>
          {{ link.label }}
        </router-link>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(8px);
}
.nav-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 1.5rem;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 0.5px;
}
.nav-links {
  display: flex;
  gap: 0.25rem;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.92rem;
  transition: all 0.15s;
}
.nav-link:hover {
  color: var(--text);
  background: var(--bg-hover);
}
.nav-link.active {
  color: var(--accent);
  background: var(--accent-dim);
}
.nav-icon {
  font-size: 1rem;
}

@media (max-width: 768px) {
  .nav-inner { padding: 0 0.75rem; }
  .nav-link { padding: 0.4rem 0.55rem; font-size: 0.8rem; }
  .nav-icon { display: none; }
}
</style>
