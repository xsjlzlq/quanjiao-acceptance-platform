<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">
        <div class="logo-icon-box">
          <van-icon name="shield-o" size="36" color="#fff" />
        </div>
        <h2 class="login-title">全椒县二轮延包验收管理平台</h2>
        <p class="login-sub">县级自查内业与外业核查系统</p>
      </div>

      <van-form @submit="onLogin" class="login-form">
        <van-field
          v-model="username"
          name="username"
          label="账号"
          placeholder="请输入账号"
          :rules="[{ required: true, message: '请输入账号' }]"
          left-icon="contact"
          clearable
        />
        <van-field
          v-model="password"
          type="password"
          name="password"
          label="密码"
          placeholder="请输入密码"
          :rules="[{ required: true, message: '请输入密码' }]"
          left-icon="lock"
          clearable
        />
        <div class="login-btn-wrap">
          <van-button
            round block type="primary"
            native-type="submit"
            :loading="loading"
            loading-text="登录中..."
            class="login-btn"
          >登 录</van-button>
        </div>
        <p v-if="errMsg" class="login-err">{{ errMsg }}</p>
      </van-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();
const username = ref('');
const password = ref('');
const loading  = ref(false);
const errMsg   = ref('');

const onLogin = async () => {
  errMsg.value = '';
  loading.value = true;
  try {
    const res = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value,
    });
    if (res.data.code === 200) {
      localStorage.setItem('auth_token',    res.data.token);
      localStorage.setItem('auth_username', res.data.username);
      localStorage.setItem('auth_role',     res.data.role);
      localStorage.setItem('auth_perms',    JSON.stringify(res.data.perms));
      router.push('/');
    } else {
      errMsg.value = res.data.message || '登录失败';
    }
  } catch (e) {
    errMsg.value = '网络异常，请稍后重试';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  position: relative;
  background-color: #eaf7ee;
  background-image: url('/farmland-bg.svg');
  background-repeat: no-repeat;
  background-position: center bottom;
  background-size: cover;
  background-attachment: fixed;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.login-card {
  width: 100%;
  max-width: 390px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 18px;
  box-shadow: 0 16px 40px rgba(45, 117, 74, 0.16), 0 2px 6px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.85);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.login-logo {
  background: linear-gradient(135deg, #2e9b5f 0%, #1d7b46 100%);
  padding: 34px 24px 26px;
  text-align: center;
  position: relative;
}

.login-logo::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 0;
  right: 0;
  height: 20px;
  background: rgba(255, 255, 255, 0.94);
  border-radius: 50% 50% 0 0 / 100% 100% 0 0;
}

.logo-icon-box {
  width: 58px;
  height: 58px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.22);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.login-title {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 6px;
  line-height: 1.4;
  letter-spacing: 0.5px;
}

.login-sub {
  color: rgba(255, 255, 255, 0.88);
  font-size: 13px;
  margin: 0;
}

.login-form {
  padding: 18px 8px 24px;
}

.login-btn-wrap {
  margin: 22px 16px 0;
}

.login-btn {
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #2e9b5f 0%, #1d7b46 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(46, 155, 95, 0.35);
}

.login-btn:active {
  opacity: 0.9;
}

.login-err {
  text-align: center;
  color: #ee0a24;
  font-size: 13px;
  margin: 12px 0 0;
}
</style>
