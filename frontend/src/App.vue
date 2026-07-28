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
      <el-menu :default-active="active" @select="selectMenu">
        <el-menu-item index="dashboard">数据概览</el-menu-item>
        <el-menu-item index="projects">项目环境</el-menu-item>
        <el-menu-item index="apis">接口管理</el-menu-item>
        <el-menu-item index="cases">用例管理</el-menu-item>
        <el-menu-item index="execute">执行中心</el-menu-item>
        <el-menu-item index="reports">报告中心</el-menu-item>
        <el-menu-item index="logs">日志中心</el-menu-item>
        <el-sub-menu index="system">
          <template #title>系统管理</template>
          <el-menu-item index="accounts">用户管理</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-spacer"></div>
        <el-dropdown trigger="click" @command="handleUserCommand">
          <button class="user-menu-trigger">
            <el-avatar :size="32">{{ avatarText }}</el-avatar>
            <span>{{ me.username }}</span>
            <span class="user-menu-arrow">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main>
        <section v-if="active === 'dashboard'" class="grid">
          <el-card><h3>项目数</h3><strong>{{ projects.length }}</strong></el-card>
          <el-card><h3>接口数</h3><strong>{{ apis.length }}</strong></el-card>
          <el-card><h3>用例数</h3><strong>{{ cases.length }}</strong></el-card>
          <el-card><h3>执行任务</h3><strong>{{ executions.length }}</strong></el-card>
        </section>

        <section v-if="active === 'accounts'">
          <div class="toolbar"><h2>用户管理</h2><el-button v-if="me.role === 'admin'" type="primary" @click="openCreateUserDialog">创建测试人员</el-button></div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="用户名">
              <el-input v-model="userSearch.username" placeholder="请输入用户名" clearable @keyup.enter="searchUsers" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="userSearch.status" placeholder="请选择状态" clearable>
                <el-option label="启用" value="active" />
                <el-option label="禁用" value="disabled" />
              </el-select>
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchUsers">搜索</el-button>
              <el-button @click="resetUserSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="users">
            <el-table-column prop="username" label="用户名" />
            <el-table-column prop="real_name" label="姓名" />
            <el-table-column prop="role" label="角色" />
            <el-table-column label="状态">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'warning'" effect="dark">
                  {{ statusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEditUserDialog(row)">编辑</el-button>
                <el-button
                  size="small"
                  :type="row.status === 'active' ? 'warning' : 'success'"
                  @click="toggleUserStatus(row)"
                >
                  {{ row.status === 'active' ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="userPagination.page"
              :page-size="userPagination.pageSize"
              :total="userPagination.total"
              @current-change="changeUserPage"
            />
          </div>

          <el-dialog v-model="createUserDialogVisible" title="创建账号" width="420px" @closed="resetUserForm">
            <el-form label-position="top" @submit.prevent="createUser">
              <el-form-item label="用户名">
                <el-input v-model="userForm.username" placeholder="请输入用户名" />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="userForm.real_name" placeholder="请输入姓名" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelCreateUser">取消</el-button>
              <el-button type="primary" @click="createUser">确认</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="editUserDialogVisible" title="编辑账号" width="420px" @closed="resetEditUserForm">
            <el-form label-position="top" @submit.prevent="updateUser">
              <el-form-item label="用户名">
                <el-input v-model="editUserForm.username" placeholder="请输入用户名" />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="editUserForm.real_name" placeholder="请输入姓名" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelEditUser">取消</el-button>
              <el-button type="primary" @click="updateUser">确认</el-button>
            </template>
          </el-dialog>
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

        <el-dialog v-model="changePasswordDialogVisible" title="修改密码" width="420px" @closed="resetChangePasswordForm">
          <el-form label-position="top" @submit.prevent="changePassword">
            <el-form-item label="原密码">
              <el-input v-model="changePasswordForm.old_password" type="password" show-password placeholder="请输入原密码" />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input
                v-model="changePasswordForm.new_password"
                type="password"
                show-password
                placeholder="请输入新密码"
                @blur="validatePasswordMatch"
              />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input
                v-model="changePasswordForm.confirm_password"
                type="password"
                show-password
                placeholder="请再次输入新密码"
                @blur="validatePasswordMatch"
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="cancelChangePassword">取消</el-button>
            <el-button type="primary" @click="changePassword">确认</el-button>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type User } from './api'

const active = ref(localStorage.getItem('active_menu') || 'dashboard')
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

const loginForm = reactive({ username: '', password: '' })
const userSearch = reactive({ username: '', status: '' })
const userPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const createUserDialogVisible = ref(false)
const editUserDialogVisible = ref(false)
const changePasswordDialogVisible = ref(false)
const userForm = reactive({ username: '', real_name: '' })
const editUserForm = reactive({ id: undefined as number | undefined, username: '', real_name: '' })
const changePasswordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const projectForm = reactive({ name: '', description: '' })
const envForm = reactive({ project_id: undefined as number | undefined, name: 'test', base_url: '' })
const apiForm = reactive({ project_id: undefined as number | undefined, module: '', name: '', method: 'GET', path: '', headersText: '{}', queryText: '{}', bodyText: '{}' })
const caseForm = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '', priority: 'P2', assertionsText: '[{"type":"status_code","expected":200}]', extractorsText: '[]' })
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })
const avatarText = computed(() => me.value?.username.slice(0, 1).toUpperCase() || 'U')

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
  calls.push(loadUsers())
  await Promise.allSettled(calls)
}

async function loadUsers() {
  const username = userSearch.username.trim()
  const status = userSearch.status
  const { data } = await api.get('/users', {
    params: {
      ...(username ? { username } : {}),
      ...(status ? { status } : {}),
      page: userPagination.page,
      page_size: userPagination.pageSize
    }
  })
  users.value = data.items
  userPagination.total = data.total
  userPagination.page = data.page
  userPagination.pageSize = data.page_size
}

async function searchUsers() {
  userPagination.page = 1
  await loadUsers()
}

async function resetUserSearch() {
  userSearch.username = ''
  userSearch.status = ''
  userPagination.page = 1
  await loadUsers()
}

async function changeUserPage(page: number) {
  userPagination.page = page
  await loadUsers()
}

async function login() {
  try {
    const { data } = await api.post('/auth/login', loginForm)
    localStorage.setItem('session_token', data.token)
    me.value = data.user
    await loadAll()
  } catch {
    ElMessage.error('用户名或密码错误')
  }
}

async function logout() {
  await api.post('/auth/logout')
  localStorage.removeItem('session_token')
  localStorage.removeItem('active_menu')
  active.value = 'dashboard'
  me.value = null
}

function selectMenu(index: string) {
  active.value = index
  localStorage.setItem('active_menu', index)
}

async function handleUserCommand(command: string) {
  if (command === 'logout') {
    await logout()
  } else if (command === 'changePassword') {
    changePasswordDialogVisible.value = true
  }
}

function resetChangePasswordForm() {
  changePasswordForm.old_password = ''
  changePasswordForm.new_password = ''
  changePasswordForm.confirm_password = ''
}

function cancelChangePassword() {
  changePasswordDialogVisible.value = false
  resetChangePasswordForm()
}

function passwordsMismatch() {
  return Boolean(
    changePasswordForm.new_password &&
    changePasswordForm.confirm_password &&
    changePasswordForm.new_password !== changePasswordForm.confirm_password
  )
}

function validatePasswordMatch() {
  if (passwordsMismatch()) {
    ElMessage.warning('两次输入的新密码不一致')
    return false
  }
  return true
}

async function changePassword() {
  if (!changePasswordForm.old_password) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (!changePasswordForm.new_password) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (changePasswordForm.new_password.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  if (!changePasswordForm.confirm_password) {
    ElMessage.warning('请再次输入新密码')
    return
  }
  if (passwordsMismatch()) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (changePasswordForm.old_password === changePasswordForm.new_password) {
    ElMessage.warning('新密码不能与原密码一致')
    return
  }
  try {
    await api.post('/auth/change-password', {
      old_password: changePasswordForm.old_password,
      new_password: changePasswordForm.new_password
    })
    changePasswordDialogVisible.value = false
    resetChangePasswordForm()
    ElMessage.success('密码修改成功')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '原密码错误')
  }
}

function resetUserForm() {
  userForm.username = ''
  userForm.real_name = ''
}

function openCreateUserDialog() {
  createUserDialogVisible.value = true
}

function cancelCreateUser() {
  createUserDialogVisible.value = false
  resetUserForm()
}

function resetEditUserForm() {
  editUserForm.id = undefined
  editUserForm.username = ''
  editUserForm.real_name = ''
}

function openEditUserDialog(user: any) {
  editUserForm.id = user.id
  editUserForm.username = user.username
  editUserForm.real_name = user.real_name
  editUserDialogVisible.value = true
}

function cancelEditUser() {
  editUserDialogVisible.value = false
  resetEditUserForm()
}

function statusText(status: string) {
  return status === 'active' ? '启用' : '禁用'
}

async function createUser() {
  const username = userForm.username.trim()
  const realName = userForm.real_name.trim()
  if (!username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!realName) {
    ElMessage.warning('请输入姓名')
    return
  }
  await api.post('/users', {
    username,
    password: '123456',
    real_name: realName,
    role: 'tester'
  })
  createUserDialogVisible.value = false
  resetUserForm()
  ElMessage.success('用户已创建')
  await loadUsers()
}

async function updateUser() {
  const username = editUserForm.username.trim()
  const realName = editUserForm.real_name.trim()
  if (!username) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!realName) {
    ElMessage.warning('请输入姓名')
    return
  }
  await api.put(`/users/${editUserForm.id}`, { username, real_name: realName })
  editUserDialogVisible.value = false
  resetEditUserForm()
  ElMessage.success('用户已更新')
  await loadUsers()
}

async function toggleUserStatus(user: any) {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  await api.patch(`/users/${user.id}/status`, { status: nextStatus })
  ElMessage.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
  await loadUsers()
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
