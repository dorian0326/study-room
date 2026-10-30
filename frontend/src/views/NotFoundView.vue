<script setup>
import jumpUrl from '../assets/nailong/nailong-jump.webp'
</script>

<template>
  <section class="nf">
    <img :src="jumpUrl" alt="奶龙跳舞" class="nl-art" />
    <h2>这个页面不存在</h2>
    <p class="hint">奶龙找了一圈也没找到，可能链接写错了或页面已被移除。</p>
    <RouterLink to="/" class="home-btn">回到首页</RouterLink>
  </section>
</template>

<style scoped>
.nf {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 48px 16px;
  text-align: center;
}
.nf img {
  width: 150px;
}
.home-btn {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 22px;
  border-radius: 9999px;
  background: var(--brand);
  color: #fff;
  font-weight: 700;
}
.home-btn:hover {
  text-decoration: none;
  background: var(--brand-hover);
}
</style>
