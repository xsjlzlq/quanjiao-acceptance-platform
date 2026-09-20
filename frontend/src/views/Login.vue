<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">
        <div class="logo-icon-box">
          <van-icon name="shield-o" size="36" color="#fff" />
        </div>
        <h2 class="login-title">二轮延包验收管理平台</h2>
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

        <!-- 纯本地图形验证码组件，0 外部网络依赖 -->
        <van-field
          v-model="captchaCode"
          name="captchaCode"
          label="验证码"
          placeholder="请输入4位验证码"
          maxlength="4"
          autocomplete="off"
          :rules="[{ required: true, message: '请输入验证码' }]"
          left-icon="shield-o"
          clearable
        >
          <template #button>
            <div class="captcha-img-box" @click="fetchCaptcha" title="看不清？点击更换验证码">
              <img v-if="captchaImg" :src="captchaImg" alt="验证码" class="captcha-img" />
              <span v-else class="captcha-loading-text">加载中...</span>
            </div>
          </template>
        </van-field>

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
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast } from 'vant';
import axios from 'axios';

const router = useRouter();
const username = ref('');
const password = ref('');
const loading  = ref(false);
const errMsg   = ref('');

// 本地图形验证码管理
const captchaId = ref('');
const captchaCode = ref('');
const captchaImg = ref('');
const captchaLoading = ref(false);

const fetchCaptcha = async () => {
  captchaLoading.value = true;
  try {
    const res = await axios.get('/api/auth/captcha');
    if (res.data && res.data.code === 200) {
      captchaId.value = res.data.captcha_id;
      captchaImg.value = res.data.image;
      captchaCode.value = '';
    } else {
      errMsg.value = res.data?.message || '获取验证码失败';
    }
  } catch (e) {
    errMsg.value = '验证码加载失败，请检查网络';
  } finally {
    captchaLoading.value = false;
  }
};

onMounted(() => {
  // 进入登录页时彻底清理残留历史会话缓存，防止上个账号或管理员的旧库信息污染新登录账号
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_username');
  localStorage.removeItem('auth_role');
  localStorage.removeItem('auth_perms');
  localStorage.removeItem('auth_target_db');
  localStorage.removeItem('auth_county_name');
  fetchCaptcha();
});

const onLogin = async () => {
  if (loading.value) return; // 正在提交中强行拦截并发与连击请求，防止产生双发请求竞态
  errMsg.value = '';
  if (!captchaCode.value.trim()) {
    showToast('请输入图形验证码');
    errMsg.value = '请输入图形验证码';
    return;
  }

  loading.value = true;
  try {
    const res = await axios.post('/api/auth/login', {
      username: username.value.trim(),
      password: password.value,
      captcha_id: captchaId.value,
      captcha_code: captchaCode.value.trim()
    });
    if (res.data.code === 200) {
      errMsg.value = '';
      localStorage.setItem('auth_token',      res.data.token);
      localStorage.setItem('auth_username',   res.data.username);
      localStorage.setItem('auth_role',       res.data.role);
      localStorage.setItem('auth_perms',      JSON.stringify(res.data.perms));
      localStorage.setItem('auth_target_db',  res.data.target_db || '');
      localStorage.setItem('auth_county_name',res.data.county_name || '');
      router.push('/');
    } else {
      errMsg.value = res.data.message || '登录失败';
      // 登录失败自动刷新验证码
      await fetchCaptcha();
    }
  } catch (e) {
    errMsg.value = '网络异常，请稍后重试';
    await fetchCaptcha();
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

.captcha-img-box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 108px;
  height: 36px;
  cursor: pointer;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ebedf0;
  background: #f7f8fa;
  user-select: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.captcha-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.captcha-loading-text {
  font-size: 12px;
  color: #969799;
}

.login-btn-wrap {
  margin: 20px 16px 0;
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
