<template>
  <div v-if="!me" class="login-page">
    <el-card class="login-card">
      <h1>接口自动化测试平台</h1>
      <el-form label-position="top" @submit.prevent="login">
        <el-form-item label="用户名"><el-input v-model="loginForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
        <el-button type="primary" class="full" @click="login">登录</el-button>
      </el-form>
    </el-card>
  </div>

  <el-container v-else class="shell">
    <el-aside width="220px">
      <div class="brand">接口测试平台</div>
      <el-menu :default-active="active" @select="active = $event">
        <el-menu-item index="dashboard">平台管理</el-menu-item>
        <el-menu-item index="accounts" v-if="me.role === 'admin'">账号管理</el-menu-item>
        <el-menu-item index="projects">项目环境</el-menu-item>
        <el-menu-item index="apis">接口管理</el-menu-item>
        <el-menu-item index="cases">用例管理</el-menu-item>
        <el-menu-item index="execute">执行中心</el-menu-item>
        <el-menu-item index="reports">报告中心</el-menu-item>
        <el-menu-item index="logs">日志中心</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <span>{{ me.real_name || me.username }} · {{ me.role === 'admin' ? '管理员' : '测试人员' }}</span>
        <el-button @click="logout">退出</el-button>
      </el-header>
      <el-main>
        <section v-if="active === 'dashboard'" class="grid">
          <el-card><h3>项目数</h3><strong>{{ projects.length }}</strong></el-card>
          <el-card><h3>接口数</h3><strong>{{ apis.length }}</strong></el-card>
          <el-card><h3>用例数</h3><strong>{{ cases.length }}</strong></el-card>
          <el-card><h3>执行任务</h3><strong>{{ executions.length }}</strong></el-card>
        </section>

        <section v-if="active === 'accounts' && me.role === 'admin'">
          <div class="toolbar"><h2>账号管理</h2><el-button type="primary" @click="createUser">创建测试人员</el-button></div>
          <el-form class="inline-form" :model="userForm">
            <el-input v-model="userForm.username" placeholder="用户名" />
            <el-input v-model="userForm.real_name" placeholder="真实姓名" />
            <el-input v-model="userForm.password" placeholder="初始密码" type="password" />
          </el-form>
          <el-table :data="users"><el-table-column prop="username" label="用户名" /><el-table-column prop="real_name" label="姓名" /><el-table-column prop="role" label="角色" /><el-table-column prop="status" label="状态" /></el-table>
        </section>

        <section v-if="active === 'projects'">
          <div class="toolbar"><h2>项目环境</h2><el-button type="primary" @click="createProject">创建项目</el-button></div>
          <el-form class="inline-form"><el-input v-model="projectForm.name" placeholder="项目名称" /><el-input v-model="projectForm.description" placeholder="描述" /></el-form>
          <el-table :data="projects" @row-click="selectedProject = $event"><el-table-column prop="name" label="项目" /><el-table-column prop="description" label="描述" /><el-table-column prop="status" label="状态" /></el-table>
          <div class="toolbar sub"><h3>环境配置</h3><el-button @click="createEnvironment">新增环境</el-button></div>
          <el-form class="inline-form"><el-select v-model="envForm.project_id" placeholder="项目"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select><el-input v-model="envForm.name" placeholder="环境名" /><el-input v-model="envForm.base_url" placeholder="Base URL" /></el-form>
          <el-table :data="environments"><el-table-column prop="name" label="环境" /><el-table-column prop="base_url" label="Base URL" /></el-table>
        </section>

        <section v-if="active === 'apis'">
          <div class="toolbar"><h2>接口管理</h2><el-button type="primary" @click="createApi">保存接口</el-button></div>
          <el-form label-position="top" class="form-grid">
            <el-form-item label="项目"><el-select v-model="apiForm.project_id"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
            <el-form-item label="模块"><el-input v-model="apiForm.module" /></el-form-item>
            <el-form-item label="名称"><el-input v-model="apiForm.name" /></el-form-item>
            <el-form-item label="方法"><el-select v-model="apiForm.method"><el-option v-for="m in methods" :key="m" :label="m" :value="m" /></el-select></el-form-item>
            <el-form-item label="路径"><el-input v-model="apiForm.path" placeholder="/users" /></el-form-item>
            <el-form-item label="Query 参数 JSON"><el-input v-model="apiForm.queryText" /></el-form-item>
            <el-form-item label="Body JSON" class="wide"><el-input v-model="apiForm.bodyText" type="textarea" :rows="4" /></el-form-item>
            <el-form-item label="Headers JSON" class="wide"><el-input v-model="apiForm.headersText" type="textarea" :rows="3" /></el-form-item>
          </el-form>
          <el-table :data="apis"><el-table-column prop="name" label="接口" /><el-table-column prop="method" label="方法" /><el-table-column prop="path" label="路径" /></el-table>
        </section>

        <section v-if="active === 'cases'">
          <div class="toolbar"><h2>用例管理</h2><el-button type="primary" @click="createCase">保存用例</el-button></div>
          <el-form label-position="top" class="form-grid">
            <el-form-item label="项目"><el-select v-model="caseForm.project_id"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
            <el-form-item label="接口"><el-select v-model="caseForm.api_id"><el-option v-for="a in apis" :key="a.id" :label="a.name" :value="a.id" /></el-select></el-form-item>
            <el-form-item label="用例名称"><el-input v-model="caseForm.name" /></el-form-item>
            <el-form-item label="优先级"><el-select v-model="caseForm.priority"><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /></el-select></el-form-item>
            <el-form-item label="断言配置 JSON" class="wide"><el-input v-model="caseForm.assertionsText" type="textarea" :rows="5" /></el-form-item>
            <el-form-item label="变量提取 JSON" class="wide"><el-input v-model="caseForm.extractorsText" type="textarea" :rows="4" /></el-form-item>
          </el-form>
          <el-table :data="cases"><el-table-column prop="name" label="用例" /><el-table-column prop="priority" label="优先级" /><el-table-column prop="status" label="状态" /></el-table>
        </section>

        <section v-if="active === 'execute'">
          <div class="toolbar"><h2>执行中心</h2><el-button type="primary" @click="runCase">手动执行</el-button></div>
          <el-form class="inline-form"><el-select v-model="execForm.project_id" placeholder="项目"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select><el-select v-model="execForm.environment_id" placeholder="环境"><el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" /></el-select><el-select v-model="execForm.target_id" placeholder="用例"><el-option v-for="c in cases" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form>
          <el-table :data="executions"><el-table-column prop="id" label="任务" /><el-table-column prop="status" label="状态" /><el-table-column prop="create_date" label="创建时间" /></el-table>
        </section>

        <section v-if="active === 'reports'">
          <h2>报告中心</h2>
          <el-table :data="executions"><el-table-column prop="id" label="任务" /><el-table-column prop="status" label="状态" /><el-table-column label="HTML 报告"><template #default="{ row }"><el-link :href="`/api/executions/${row.id}/report`" target="_blank">查看报告</el-link></template></el-table-column></el-table>
        </section>

        <section v-if="active === 'logs'">
          <h2>日志中心</h2>
          <el-table :data="logs"><el-table-column prop="module" label="模块" /><el-table-column prop="action" label="操作" /><el-table-column prop="result" label="结果" /><el-table-column prop="create_date" label="时间" /></el-table>
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type User } from './api'

const active = ref('dashboard')
const me = ref<User | null>(null)
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const users = ref<any[]>([])
const projects = ref<any[]>([])
const environments = ref<any[]>([])
const apis = ref<any[]>([])
const cases = ref<any[]>([])
const executions = ref<any[]>([])
const logs = ref<any[]>([])
const selectedProject = ref<any>(null)

const loginForm = reactive({ username: 'admin', password: 'admin123' })
const userForm = reactive({ username: '', real_name: '', password: '123456', role: 'tester' })
const projectForm = reactive({ name: '', description: '' })
const envForm = reactive({ project_id: undefined as number | undefined, name: 'test', base_url: '' })
const apiForm = reactive({ project_id: undefined as number | undefined, module: '', name: '', method: 'GET', path: '', headersText: '{}', queryText: '{}', bodyText: '{}' })
const caseForm = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '', priority: 'P2', assertionsText: '[{"type":"status_code","expected":200}]', extractorsText: '[]' })
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })

function parseJson(text: string, fallback: any) {
  try { return JSON.parse(text || '') } catch { return fallback }
}

async function loadAll() {
  const calls = [
    api.get('/projects').then(r => projects.value = r.data),
    api.get('/environments').then(r => environments.value = r.data),
    api.get('/apis').then(r => apis.value = r.data),
    api.get('/cases').then(r => cases.value = r.data),
    api.get('/executions').then(r => executions.value = r.data),
    api.get('/logs').then(r => logs.value = r.data)
  ]
  if (me.value?.role === 'admin') calls.push(api.get('/users').then(r => users.value = r.data))
  await Promise.allSettled(calls)
}

async function login() {
  const { data } = await api.post('/auth/login', loginForm)
  localStorage.setItem('session_token', data.token)
  me.value = data.user
  await loadAll()
}

async function logout() {
  await api.post('/auth/logout')
  localStorage.removeItem('session_token')
  me.value = null
}

async function createUser() {
  await api.post('/users', userForm)
  ElMessage.success('账号已创建')
  await loadAll()
}

async function createProject() {
  await api.post('/projects', projectForm)
  projectForm.name = ''
  projectForm.description = ''
  await loadAll()
}

async function createEnvironment() {
  await api.post('/environments', { ...envForm, headers: {}, variables: {} })
  await loadAll()
}

async function createApi() {
  await api.post('/apis', { ...apiForm, headers: parseJson(apiForm.headersText, {}), query: parseJson(apiForm.queryText, {}), body: parseJson(apiForm.bodyText, {}) })
  await loadAll()
}

async function createCase() {
  await api.post('/cases', { ...caseForm, assertions: parseJson(caseForm.assertionsText, []), extractors: parseJson(caseForm.extractorsText, []), request_headers: {}, request_query: {}, request_body: {} })
  await loadAll()
}

async function runCase() {
  await api.post('/executions', { ...execForm, target_type: 'case' })
  ElMessage.success('执行任务已提交')
  await loadAll()
}

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    me.value = data
    await loadAll()
  } catch {}
})
</script>
