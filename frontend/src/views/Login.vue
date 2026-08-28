<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">
        <div class="logo-icon-box">
          <van-icon name="shield-o" size="36" color="#fff" />
        </div>
        <h2 class="login-title">全椒县二轮延包验收管理平台</h2>
        <p class="login-sub">县级自查验收系统</p>
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
          >登录</van-button>
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
  background: linear-gradient(145deg, #e8f4fd 0%, #dceefb 50%, #c9e4f8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(25, 137, 250, 0.12);
  overflow: hidden;
}
.login-logo {
  background: linear-gradient(135deg, #1989fa 0%, #0d6ecc 100%);
  padding: 36px 24px 28px;
  text-align: center;
}
.logo-icon-box {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.login-title {
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 6px;
  line-height: 1.4;
}
.login-sub {
  color: rgba(255,255,255,0.8);
  font-size: 13px;
  margin: 0;
}
.login-form {
  padding: 8px 0 24px;
}
.login-btn-wrap {
  margin: 20px 16px 0;
}
.login-btn {
  height: 44px;
  font-size: 16px;
}
.login-err {
  text-align: center;
  color: #ee0a24;
  font-size: 13px;
  margin: 10px 0 0;
}
</style>