<template>
  <div v-if="!me" class="login-page">
    <el-card class="login-card">
      <div class="login-brand">
        <span class="brand-mark">API</span>
        <div>
          <h1>接口自动化测试平台</h1>
          <p>统一管理接口、用例、执行任务与测试报告</p>
        </div>
      </div>
      <el-form label-position="top" @submit.prevent="login">
        <el-form-item label="用户名"><el-input v-model="loginForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
        <el-button type="primary" class="full" @click="login">登录</el-button>
      </el-form>
    </el-card>
  </div>

  <el-container v-else class="shell">
    <el-aside width="220px">
      <div class="brand">
        <span class="brand-logo">API</span>
        <span>接口测试平台</span>
      </div>
      <el-menu :default-active="active" @select="selectMenu">
        <el-menu-item index="dashboard">数据概览</el-menu-item>
        <el-sub-menu index="project-env">
          <template #title>项目环境</template>
          <el-menu-item index="projects">项目管理</el-menu-item>
          <el-menu-item index="environments">环境管理</el-menu-item>
        </el-sub-menu>
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
        <div class="header-title">
          <strong>{{ activeLabel }}</strong>
          <span>专业、稳定、可追踪的接口测试工作台</span>
        </div>
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
      <div class="tabs-bar">
        <el-tabs
          v-model="active"
          type="card"
          @tab-change="switchTab"
          @tab-remove="closeTab"
        >
          <el-tab-pane
            v-for="tab in openedTabs"
            :key="tab.name"
            :label="tab.label"
            :name="tab.name"
            :closable="tab.closable"
          />
        </el-tabs>
      </div>
      <el-main>
        <section v-if="active === 'dashboard'" class="page-section dashboard-page">
          <div class="page-heading">
            <div>
              <h2>数据概览</h2>
              <p>快速掌握测试资产与执行任务规模</p>
            </div>
          </div>
          <div class="grid">
            <el-card class="metric-card metric-projects">
              <span class="metric-icon">项</span>
              <div>
                <h3>项目数</h3>
                <strong>{{ projects.length }}</strong>
                <p>当前维护的测试项目</p>
              </div>
            </el-card>
            <el-card class="metric-card metric-apis">
              <span class="metric-icon">接</span>
              <div>
                <h3>接口数</h3>
                <strong>{{ apis.length }}</strong>
                <p>已登记的接口资产</p>
              </div>
            </el-card>
            <el-card class="metric-card metric-cases">
              <span class="metric-icon">例</span>
              <div>
                <h3>用例数</h3>
                <strong>{{ cases.length }}</strong>
                <p>可执行测试用例</p>
              </div>
            </el-card>
            <el-card class="metric-card metric-executions">
              <span class="metric-icon">执</span>
              <div>
                <h3>执行任务</h3>
                <strong>{{ executions.length }}</strong>
                <p>历史与当前执行记录</p>
              </div>
            </el-card>
          </div>
        </section>

        <section v-if="active === 'accounts'" class="page-section">
          <div class="toolbar"><h2>用户管理</h2><el-button v-if="me.role === 'admin'" type="primary" @click="openCreateUserDialog">创建测试人员</el-button></div>
          <el-form class="search-form panel" label-position="top">
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
          <div class="table-panel"><el-table :data="users">
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
          </el-table></div>
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

        <section v-if="active === 'projects'" class="page-section">
          <div class="toolbar"><h2>项目管理</h2><el-button type="primary" @click="openCreateProjectDialog">创建项目</el-button></div>
          <el-form class="search-form panel" label-position="top">
            <el-form-item label="项目名称">
              <el-input v-model="projectSearch.name" placeholder="请输入项目名称" clearable @keyup.enter="searchProjects" />
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchProjects">搜索</el-button>
              <el-button @click="resetProjectSearch">重置</el-button>
            </div>
          </el-form>
          <div class="table-panel"><el-table :data="projectList">
            <el-table-column prop="name" label="项目" />
            <el-table-column prop="description" label="描述" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEditProjectDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table></div>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="projectPagination.page"
              :page-size="projectPagination.pageSize"
              :total="projectPagination.total"
              @current-change="changeProjectPage"
            />
          </div>

          <el-dialog v-model="createProjectDialogVisible" title="创建项目" width="420px" @closed="resetProjectForm">
            <el-form label-position="top" @submit.prevent="createProject">
              <el-form-item label="项目名称">
                <el-input v-model="projectForm.name" placeholder="请输入项目名称" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="projectForm.description" placeholder="请输入描述" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelCreateProject">取消</el-button>
              <el-button type="primary" @click="createProject">确认</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="editProjectDialogVisible" title="编辑项目" width="420px" @closed="resetEditProjectForm">
            <el-form label-position="top" @submit.prevent="updateProject">
              <el-form-item label="项目名称">
                <el-input v-model="editProjectForm.name" placeholder="请输入项目名称" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="editProjectForm.description" placeholder="请输入描述" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelEditProject">取消</el-button>
              <el-button type="primary" @click="updateProject">确认</el-button>
            </template>
          </el-dialog>
        </section>

        <section v-if="active === 'environments'" class="page-section">
          <div class="toolbar"><h2>环境管理</h2><el-button type="primary" @click="openCreateEnvironmentDialog">新增环境</el-button></div>
          <el-form class="search-form panel" label-position="top">
            <el-form-item label="项目">
              <el-select v-model="environmentSearch.project_id" placeholder="请选择项目" clearable>
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="环境名称">
              <el-input v-model="environmentSearch.name" placeholder="请输入环境名称" clearable @keyup.enter="searchEnvironments" />
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchEnvironments">搜索</el-button>
              <el-button @click="resetEnvironmentSearch">重置</el-button>
            </div>
          </el-form>
          <div class="table-panel"><el-table :data="environmentList">
            <el-table-column prop="project_name" label="项目" />
            <el-table-column prop="name" label="环境名称" />
            <el-table-column prop="protocol" label="协议" />
            <el-table-column prop="base_url" label="Base URL" />
            <el-table-column prop="port" label="端口号" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEditEnvironmentDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteEnvironment(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table></div>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="environmentPagination.page"
              :page-size="environmentPagination.pageSize"
              :total="environmentPagination.total"
              @current-change="changeEnvironmentPage"
            />
          </div>

          <el-dialog v-model="createEnvironmentDialogVisible" title="新增环境" width="420px" @closed="resetEnvironmentForm">
            <el-form label-position="top" @submit.prevent="createEnvironment">
              <el-form-item label="项目">
                <el-select v-model="envForm.project_id" placeholder="请选择项目">
                  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="环境名称">
                <el-input v-model="envForm.name" placeholder="请输入环境名称" />
              </el-form-item>
              <el-form-item label="协议">
                <el-select v-model="envForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(envForm.protocol)">
                  <el-option label="http" value="http" />
                  <el-option label="https" value="https" />
                </el-select>
              </el-form-item>
              <el-form-item label="Base URL">
                <el-input v-model="envForm.base_url" placeholder="请输入 Base URL" />
              </el-form-item>
              <el-form-item label="端口号">
                <el-input v-model="envForm.port" placeholder="请输入端口号" @input="envForm.port = digitsOnly(envForm.port)" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelCreateEnvironment">取消</el-button>
              <el-button type="primary" @click="createEnvironment">确认</el-button>
            </template>
          </el-dialog>

          <el-dialog v-model="editEnvironmentDialogVisible" title="编辑环境" width="420px" @closed="resetEditEnvironmentForm">
            <el-form label-position="top" @submit.prevent="updateEnvironment">
              <el-form-item label="项目">
                <el-select v-model="editEnvironmentForm.project_id" placeholder="请选择项目">
                  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="环境名称">
                <el-input v-model="editEnvironmentForm.name" placeholder="请输入环境名称" />
              </el-form-item>
              <el-form-item label="协议">
                <el-select v-model="editEnvironmentForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(editEnvironmentForm.protocol)">
                  <el-option label="http" value="http" />
                  <el-option label="https" value="https" />
                </el-select>
              </el-form-item>
              <el-form-item label="Base URL">
                <el-input v-model="editEnvironmentForm.base_url" placeholder="请输入 Base URL" />
              </el-form-item>
              <el-form-item label="端口号">
                <el-input v-model="editEnvironmentForm.port" placeholder="请输入端口号" @input="editEnvironmentForm.port = digitsOnly(editEnvironmentForm.port)" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="cancelEditEnvironment">取消</el-button>
              <el-button type="primary" @click="updateEnvironment">确认</el-button>
            </template>
          </el-dialog>
        </section>

        <section v-if="active === 'apis'" class="page-section">
          <div class="toolbar"><h2>接口管理</h2><el-button type="primary" @click="createApi">保存接口</el-button></div>
          <el-form label-position="top" class="form-grid panel">
            <el-form-item label="项目"><el-select v-model="apiForm.project_id"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
            <el-form-item label="模块"><el-input v-model="apiForm.module" /></el-form-item>
            <el-form-item label="名称"><el-input v-model="apiForm.name" /></el-form-item>
            <el-form-item label="方法"><el-select v-model="apiForm.method"><el-option v-for="m in methods" :key="m" :label="m" :value="m" /></el-select></el-form-item>
            <el-form-item label="路径"><el-input v-model="apiForm.path" placeholder="/users" /></el-form-item>
            <el-form-item label="Query 参数 JSON"><el-input v-model="apiForm.queryText" /></el-form-item>
            <el-form-item label="Body JSON" class="wide"><el-input v-model="apiForm.bodyText" type="textarea" :rows="4" /></el-form-item>
            <el-form-item label="Headers JSON" class="wide"><el-input v-model="apiForm.headersText" type="textarea" :rows="3" /></el-form-item>
          </el-form>
          <div class="table-panel"><el-table :data="apis"><el-table-column prop="name" label="接口" /><el-table-column prop="method" label="方法" /><el-table-column prop="path" label="路径" /></el-table></div>
        </section>

        <section v-if="active === 'cases'" class="page-section">
          <div class="toolbar"><h2>用例管理</h2><el-button type="primary" @click="createCase">保存用例</el-button></div>
          <el-form label-position="top" class="form-grid panel">
            <el-form-item label="项目"><el-select v-model="caseForm.project_id"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
            <el-form-item label="接口"><el-select v-model="caseForm.api_id"><el-option v-for="a in apis" :key="a.id" :label="a.name" :value="a.id" /></el-select></el-form-item>
            <el-form-item label="用例名称"><el-input v-model="caseForm.name" /></el-form-item>
            <el-form-item label="优先级"><el-select v-model="caseForm.priority"><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /></el-select></el-form-item>
            <el-form-item label="断言配置 JSON" class="wide"><el-input v-model="caseForm.assertionsText" type="textarea" :rows="5" /></el-form-item>
            <el-form-item label="变量提取 JSON" class="wide"><el-input v-model="caseForm.extractorsText" type="textarea" :rows="4" /></el-form-item>
          </el-form>
          <div class="table-panel"><el-table :data="cases"><el-table-column prop="name" label="用例" /><el-table-column prop="priority" label="优先级" /><el-table-column prop="status" label="状态" /></el-table></div>
        </section>

        <section v-if="active === 'execute'" class="page-section">
          <div class="toolbar"><h2>执行中心</h2><el-button type="primary" @click="runCase">手动执行</el-button></div>
          <el-form class="inline-form panel"><el-select v-model="execForm.project_id" placeholder="项目"><el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select><el-select v-model="execForm.environment_id" placeholder="环境"><el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" /></el-select><el-select v-model="execForm.target_id" placeholder="用例"><el-option v-for="c in cases" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form>
          <div class="table-panel"><el-table :data="executions"><el-table-column prop="id" label="任务" /><el-table-column prop="status" label="状态" /><el-table-column prop="create_date" label="创建时间" /></el-table></div>
        </section>

        <section v-if="active === 'reports'" class="page-section">
          <div class="toolbar"><h2>报告中心</h2></div>
          <div class="table-panel"><el-table :data="executions"><el-table-column prop="id" label="任务" /><el-table-column prop="status" label="状态" /><el-table-column label="HTML 报告"><template #default="{ row }"><el-link :href="`/api/executions/${row.id}/report`" target="_blank">查看报告</el-link></template></el-table-column></el-table></div>
        </section>

        <section v-if="active === 'logs'" class="page-section">
          <div class="toolbar"><h2>日志中心</h2></div>
          <div class="table-panel"><el-table :data="logs"><el-table-column prop="module" label="模块" /><el-table-column prop="action" label="操作" /><el-table-column prop="result" label="结果" /><el-table-column prop="create_date" label="时间" /></el-table></div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type User } from './api'

type AppTab = { name: string; label: string; closable: boolean }

const menuMeta: Record<string, AppTab> = {
  dashboard: { name: 'dashboard', label: '数据概览', closable: false },
  projects: { name: 'projects', label: '项目管理', closable: true },
  environments: { name: 'environments', label: '环境管理', closable: true },
  apis: { name: 'apis', label: '接口管理', closable: true },
  cases: { name: 'cases', label: '用例管理', closable: true },
  execute: { name: 'execute', label: '执行中心', closable: true },
  reports: { name: 'reports', label: '报告中心', closable: true },
  logs: { name: 'logs', label: '日志中心', closable: true },
  accounts: { name: 'accounts', label: '用户管理', closable: true }
}

function restoreTabs(): AppTab[] {
  try {
    const raw = JSON.parse(localStorage.getItem('opened_tabs') || '[]')
    if (Array.isArray(raw)) {
      const restored = raw
        .map((tab: any) => menuMeta[tab?.name])
        .filter(Boolean)
      const unique = Array.from(new Map(restored.map(tab => [tab.name, tab])).values())
      if (unique.length > 0) {
        return unique.some(tab => tab.name === 'dashboard') ? unique : [menuMeta.dashboard, ...unique]
      }
    }
  } catch {}
  return [menuMeta.dashboard]
}

function restoreActive(tabs: AppTab[]) {
  const saved = localStorage.getItem('active_menu') || 'dashboard'
  return tabs.some(tab => tab.name === saved) ? saved : 'dashboard'
}

const openedTabs = ref<AppTab[]>(restoreTabs())
const active = ref(restoreActive(openedTabs.value))

const me = ref<User | null>(null)
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const users = ref<any[]>([])
const projects = ref<any[]>([])
const projectList = ref<any[]>([])
const environments = ref<any[]>([])
const environmentList = ref<any[]>([])
const apis = ref<any[]>([])
const cases = ref<any[]>([])
const executions = ref<any[]>([])
const logs = ref<any[]>([])
const selectedProject = ref<any>(null)

const loginForm = reactive({ username: '', password: '' })
const userSearch = reactive({ username: '', status: '' })
const userPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const projectSearch = reactive({ name: '' })
const projectPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const environmentSearch = reactive({ project_id: undefined as number | undefined, name: '' })
const environmentPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const createUserDialogVisible = ref(false)
const editUserDialogVisible = ref(false)
const createProjectDialogVisible = ref(false)
const editProjectDialogVisible = ref(false)
const createEnvironmentDialogVisible = ref(false)
const editEnvironmentDialogVisible = ref(false)
const changePasswordDialogVisible = ref(false)
const userForm = reactive({ username: '', real_name: '' })
const editUserForm = reactive({ id: undefined as number | undefined, username: '', real_name: '' })
const changePasswordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const projectForm = reactive({ name: '', description: '' })
const editProjectForm = reactive({ id: undefined as number | undefined, name: '', description: '' })
const envForm = reactive({ project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const editEnvironmentForm = reactive({ id: undefined as number | undefined, project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const apiForm = reactive({ project_id: undefined as number | undefined, module: '', name: '', method: 'GET', path: '', headersText: '{}', queryText: '{}', bodyText: '{}' })
const caseForm = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '', priority: 'P2', assertionsText: '[{"type":"status_code","expected":200}]', extractorsText: '[]' })
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })
const avatarText = computed(() => me.value?.username.slice(0, 1).toUpperCase() || 'U')
const activeLabel = computed(() => menuMeta[active.value]?.label || '工作台')

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
  calls.push(loadProjects())
  calls.push(loadEnvironments())
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

async function loadProjects() {
  const name = projectSearch.name.trim()
  const { data } = await api.get('/projects', {
    params: {
      ...(name ? { name } : {}),
      page: projectPagination.page,
      page_size: projectPagination.pageSize
    }
  })
  projectList.value = data.items
  projectPagination.total = data.total
  projectPagination.page = data.page
  projectPagination.pageSize = data.page_size
}

async function searchProjects() {
  projectPagination.page = 1
  await loadProjects()
}

async function resetProjectSearch() {
  projectSearch.name = ''
  projectPagination.page = 1
  await loadProjects()
}

async function changeProjectPage(page: number) {
  projectPagination.page = page
  await loadProjects()
}

async function loadEnvironments() {
  const name = environmentSearch.name.trim()
  const projectId = environmentSearch.project_id
  const { data } = await api.get('/environments', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(name ? { name } : {}),
      page: environmentPagination.page,
      page_size: environmentPagination.pageSize
    }
  })
  environmentList.value = data.items
  environmentPagination.total = data.total
  environmentPagination.page = data.page
  environmentPagination.pageSize = data.page_size
}

async function searchEnvironments() {
  environmentPagination.page = 1
  await loadEnvironments()
}

async function resetEnvironmentSearch() {
  environmentSearch.project_id = undefined
  environmentSearch.name = ''
  environmentPagination.page = 1
  await loadEnvironments()
}

async function changeEnvironmentPage(page: number) {
  environmentPagination.page = page
  await loadEnvironments()
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
  localStorage.removeItem('opened_tabs')
  openedTabs.value = [menuMeta.dashboard]
  active.value = 'dashboard'
  me.value = null
}

function saveTabs() {
  localStorage.setItem('opened_tabs', JSON.stringify(openedTabs.value.map(tab => ({ name: tab.name }))))
  localStorage.setItem('active_menu', active.value)
}

function openTab(index: string) {
  const tab = menuMeta[index]
  if (!tab) {
    return
  }
  if (!openedTabs.value.some(item => item.name === index)) {
    openedTabs.value.push(tab)
  }
  active.value = index
  saveTabs()
}

function selectMenu(index: string) {
  openTab(index)
}

function switchTab(name: string | number) {
  active.value = String(name)
  saveTabs()
}

function closeTab(name: string | number) {
  const target = String(name)
  const index = openedTabs.value.findIndex(tab => tab.name === target)
  const tab = openedTabs.value[index]
  if (index === -1 || !tab?.closable) {
    return
  }
  openedTabs.value.splice(index, 1)
  if (openedTabs.value.length === 0) {
    openedTabs.value = [menuMeta.dashboard]
  }
  if (active.value === target) {
    const next = openedTabs.value[index - 1] || openedTabs.value[index] || menuMeta.dashboard
    active.value = next.name
  }
  saveTabs()
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

function resetProjectForm() {
  projectForm.name = ''
  projectForm.description = ''
}

function openCreateProjectDialog() {
  createProjectDialogVisible.value = true
}

function cancelCreateProject() {
  createProjectDialogVisible.value = false
  resetProjectForm()
}

function resetEditProjectForm() {
  editProjectForm.id = undefined
  editProjectForm.name = ''
  editProjectForm.description = ''
}

function openEditProjectDialog(project: any) {
  editProjectForm.id = project.id
  editProjectForm.name = project.name
  editProjectForm.description = project.description || ''
  editProjectDialogVisible.value = true
}

function cancelEditProject() {
  editProjectDialogVisible.value = false
  resetEditProjectForm()
}

async function refreshProjectsAfterChange() {
  await Promise.all([
    api.get('/projects').then(r => projects.value = r.data),
    loadProjects()
  ])
}

async function refreshProjectsAfterDelete() {
  await refreshProjectsAfterChange()
  if (projectList.value.length === 0 && projectPagination.page > 1) {
    projectPagination.page -= 1
    await loadProjects()
  }
}

async function createProject() {
  const name = projectForm.name.trim()
  const description = projectForm.description.trim()
  if (!name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!description) {
    ElMessage.warning('请输入描述')
    return
  }
  if (projects.value.some(project => project.name === name)) {
    ElMessage.warning('项目名称已存在')
    return
  }
  try {
    await api.post('/projects', { name, description })
    createProjectDialogVisible.value = false
    resetProjectForm()
    ElMessage.success('项目已创建')
    await refreshProjectsAfterChange()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '项目创建失败')
  }
}

async function updateProject() {
  const name = editProjectForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入项目名称')
    return
  }
  await api.put(`/projects/${editProjectForm.id}`, { name, description: editProjectForm.description })
  editProjectDialogVisible.value = false
  resetEditProjectForm()
  ElMessage.success('项目已更新')
  await refreshProjectsAfterChange()
}

async function deleteProject(project: any) {
  try {
    await ElMessageBox.confirm('确认删除该项目吗？', '删除项目', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/projects/${project.id}`)
  ElMessage.success('项目已删除')
  await refreshProjectsAfterDelete()
}

function resetEnvironmentForm() {
  envForm.project_id = undefined
  envForm.name = ''
  envForm.protocol = ''
  envForm.base_url = ''
  envForm.port = ''
}

function openCreateEnvironmentDialog() {
  createEnvironmentDialogVisible.value = true
}

function cancelCreateEnvironment() {
  createEnvironmentDialogVisible.value = false
  resetEnvironmentForm()
}

function resetEditEnvironmentForm() {
  editEnvironmentForm.id = undefined
  editEnvironmentForm.project_id = undefined
  editEnvironmentForm.name = ''
  editEnvironmentForm.protocol = ''
  editEnvironmentForm.base_url = ''
  editEnvironmentForm.port = ''
}

function openEditEnvironmentDialog(environment: any) {
  editEnvironmentForm.id = environment.id
  editEnvironmentForm.project_id = environment.project_id
  editEnvironmentForm.name = environment.name
  editEnvironmentForm.protocol = environment.protocol || ''
  editEnvironmentForm.base_url = environment.base_url
  editEnvironmentForm.port = environment.port ? String(environment.port) : ''
  editEnvironmentDialogVisible.value = true
}

function cancelEditEnvironment() {
  editEnvironmentDialogVisible.value = false
  resetEditEnvironmentForm()
}

async function refreshEnvironmentsAfterChange() {
  await Promise.all([
    api.get('/environments').then(r => environments.value = r.data),
    loadEnvironments()
  ])
}

async function refreshEnvironmentsAfterDelete() {
  await refreshEnvironmentsAfterChange()
  if (environmentList.value.length === 0 && environmentPagination.page > 1) {
    environmentPagination.page -= 1
    await loadEnvironments()
  }
}

function environmentNameExists(projectId: number, name: string, environmentId?: number) {
  return environments.value.some(environment =>
    environment.project_id === projectId &&
    environment.name === name &&
    environment.id !== environmentId
  )
}

function digitsOnly(value: string) {
  return String(value || '').replace(/\D/g, '')
}

function validateEnvironmentProtocol(protocol: string) {
  if (!protocol) {
    ElMessage.warning('请选择协议')
    return false
  }
  return true
}

function environmentPort(protocol: string, port: string) {
  if (port) {
    return Number(port)
  }
  return protocol === 'http' ? 80 : 443
}

async function createEnvironment() {
  const projectId = envForm.project_id
  const name = envForm.name.trim()
  const protocol = envForm.protocol
  const baseUrl = envForm.base_url.trim()
  const port = environmentPort(protocol, envForm.port)
  if (!projectId) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!name) {
    ElMessage.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    ElMessage.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    ElMessage.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name)) {
    ElMessage.warning('环境名称已存在')
    return
  }
  try {
    await api.post('/environments', { project_id: projectId, name, protocol, base_url: baseUrl, port, headers: {}, variables: {} })
    createEnvironmentDialogVisible.value = false
    resetEnvironmentForm()
    ElMessage.success('环境已创建')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '环境创建失败')
  }
}

async function updateEnvironment() {
  const projectId = editEnvironmentForm.project_id
  const name = editEnvironmentForm.name.trim()
  const protocol = editEnvironmentForm.protocol
  const baseUrl = editEnvironmentForm.base_url.trim()
  const port = environmentPort(protocol, editEnvironmentForm.port)
  if (!projectId) {
    ElMessage.warning('请选择项目')
    return
  }
  if (!name) {
    ElMessage.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    ElMessage.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    ElMessage.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name, editEnvironmentForm.id)) {
    ElMessage.warning('环境名称已存在')
    return
  }
  try {
    await api.put(`/environments/${editEnvironmentForm.id}`, { project_id: projectId, name, protocol, base_url: baseUrl, port })
    editEnvironmentDialogVisible.value = false
    resetEditEnvironmentForm()
    ElMessage.success('环境已更新')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '环境更新失败')
  }
}

async function deleteEnvironment(environment: any) {
  try {
    await ElMessageBox.confirm('确认删除该环境吗？', '删除环境', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/environments/${environment.id}`)
  ElMessage.success('环境已删除')
  await refreshEnvironmentsAfterDelete()
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
