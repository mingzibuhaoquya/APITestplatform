<template>
  <a-config-provider :locale="zhCN" :theme="appTheme">
    <div v-if="!me" class="login-page">
      <a-card class="login-card" :bordered="false">
        <div class="login-brand">
          <div class="login-logo"><img src="/company-logo.png" alt="接口测试平台" /></div>
          <div>
            <h1>接口自动化测试平台</h1>
            <p>面向测试团队的接口回归与质量协作平台</p>
          </div>
        </div>
        <a-form layout="vertical" @submit.prevent="login">
          <a-form-item label="用户名">
            <a-input v-model:value="loginForm.username" size="large" placeholder="请输入用户名">
              <template #prefix><UserOutlined /></template>
            </a-input>
          </a-form-item>
          <a-form-item label="密码">
            <a-input-password v-model:value="loginForm.password" size="large" placeholder="请输入密码">
              <template #prefix><LockOutlined /></template>
            </a-input-password>
          </a-form-item>
          <a-button type="primary" html-type="submit" size="large" class="full" :loading="loginLoading">
            <template #icon><LoginOutlined /></template>
            登录
          </a-button>
        </a-form>
      </a-card>
    </div>

    <a-layout v-else class="shell">
      <a-layout-sider
        v-if="!isMobile"
        v-model:collapsed="sidebarCollapsed"
        :trigger="null"
        :collapsed-width="72"
        breakpoint="lg"
        width="232"
        class="app-sider"
        @breakpoint="handleSidebarBreakpoint"
      >
        <div class="brand" :class="{ 'brand-collapsed': sidebarCollapsed }">
          <img src="/company-logo.png" alt="接口测试平台" />
          <span v-if="!sidebarCollapsed">接口测试平台</span>
        </div>
        <a-menu :selected-keys="[active]" mode="inline" @select="handleMenuSelect">
          <a-menu-item key="dashboard"><template #icon><DashboardOutlined /></template>数据概览</a-menu-item>
          <a-sub-menu key="project-env">
            <template #icon><FolderOpenOutlined /></template>
            <template #title>项目环境</template>
            <a-menu-item key="projects"><template #icon><ProjectOutlined /></template>项目管理</a-menu-item>
            <a-menu-item key="environments"><template #icon><CloudServerOutlined /></template>环境管理</a-menu-item>
          </a-sub-menu>
          <a-menu-item key="apis"><template #icon><ApiOutlined /></template>接口管理</a-menu-item>
          <a-menu-item key="cases"><template #icon><FileTextOutlined /></template>用例管理</a-menu-item>
          <a-menu-item key="execute"><template #icon><PlayCircleOutlined /></template>测试计划</a-menu-item>
          <a-menu-item key="reports"><template #icon><BarChartOutlined /></template>报告中心</a-menu-item>
          <a-menu-item key="logs"><template #icon><ProfileOutlined /></template>日志中心</a-menu-item>
          <a-sub-menu key="system">
            <template #icon><SettingOutlined /></template>
            <template #title>系统管理</template>
            <a-menu-item key="accounts"><template #icon><TeamOutlined /></template>用户管理</a-menu-item>
          </a-sub-menu>
        </a-menu>
      </a-layout-sider>
      <a-drawer v-else v-model:open="mobileSidebarOpen" placement="left" :closable="false" :width="232" class="mobile-nav-drawer">
        <div class="brand"><img src="/company-logo.png" alt="接口测试平台" /><span>接口测试平台</span></div>
        <a-menu :selected-keys="[active]" mode="inline" @select="handleMenuSelect">
          <a-menu-item key="dashboard"><template #icon><DashboardOutlined /></template>数据概览</a-menu-item>
          <a-sub-menu key="project-env">
            <template #icon><FolderOpenOutlined /></template>
            <template #title>项目环境</template>
            <a-menu-item key="projects"><template #icon><ProjectOutlined /></template>项目管理</a-menu-item>
            <a-menu-item key="environments"><template #icon><CloudServerOutlined /></template>环境管理</a-menu-item>
          </a-sub-menu>
          <a-menu-item key="apis"><template #icon><ApiOutlined /></template>接口管理</a-menu-item>
          <a-menu-item key="cases"><template #icon><FileTextOutlined /></template>用例管理</a-menu-item>
          <a-menu-item key="execute"><template #icon><PlayCircleOutlined /></template>测试计划</a-menu-item>
          <a-menu-item key="reports"><template #icon><BarChartOutlined /></template>报告中心</a-menu-item>
          <a-menu-item key="logs"><template #icon><ProfileOutlined /></template>日志中心</a-menu-item>
          <a-sub-menu key="system">
            <template #icon><SettingOutlined /></template>
            <template #title>系统管理</template>
            <a-menu-item key="accounts"><template #icon><TeamOutlined /></template>用户管理</a-menu-item>
          </a-sub-menu>
        </a-menu>
      </a-drawer>
      <a-layout
        class="main-layout"
        :class="{ 'main-layout-collapsed': sidebarCollapsed, 'main-layout-mobile': isMobile }"
      >
        <a-layout-header class="app-header">
          <div class="header-left">
            <a-button type="text" class="sidebar-trigger" @click="toggleSidebar">
              <template #icon><MenuUnfoldOutlined v-if="sidebarCollapsed || isMobile" /><MenuFoldOutlined v-else /></template>
            </a-button>
            <a-divider type="vertical" />
            <div class="header-page-title">
              <span class="header-eyebrow">测试工作台</span>
              <strong>{{ currentPageTitle }}</strong>
            </div>
          </div>
          <a-dropdown trigger="click">
            <button class="user-menu-trigger">
              <a-avatar :size="32" class="user-avatar">{{ avatarText }}</a-avatar>
              <span class="user-menu-name">{{ me.username }}</span>
              <DownOutlined class="user-menu-arrow" />
            </button>
            <template #overlay>
              <a-menu class="user-dropdown-menu">
                <a-menu-item key="changePassword" @click="handleUserCommand('changePassword')"><template #icon><LockOutlined /></template>修改密码</a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleUserCommand('logout')"><template #icon><LogoutOutlined /></template>退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </a-layout-header>
      <div class="tabs-bar">
        <a-tabs
          v-model:active-key="active"
          type="editable-card"
          hide-add
          @edit="handleTabEdit"
        >
          <a-tab-pane
            v-for="tab in openedTabs"
            :key="tab.name"
            :tab="tab.label"
            :closable="tab.closable"
          />
        </a-tabs>
      </div>
      <a-layout-content>
        <section v-if="active === 'dashboard'" class="dashboard-page">
          <div class="page-heading dashboard-heading">
            <div><h1>数据概览</h1><p>掌握平台配置规模与最近执行概况</p></div>
            <a-button type="default" @click="loadAll"><template #icon><ReloadOutlined /></template>刷新数据</a-button>
          </div>
          <div class="grid">
            <a-card v-for="stat in dashboardStats" :key="stat.label" class="stat-card" :class="`stat-${stat.tone}`" :bordered="false">
              <div class="stat-card-icon"><component :is="stat.icon" /></div>
              <a-statistic :title="stat.label" :value="stat.value" />
              <div class="stat-card-meta">{{ stat.description }}</div>
            </a-card>
          </div>
        </section>

        <section v-if="active === 'accounts'" class="page-view">
          <div class="toolbar"><h2>用户管理</h2><a-button v-if="me.role === 'admin'" type="primary" @click="openCreateUserDialog"><template #icon><UserAddOutlined /></template>创建测试人员</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="用户名">
              <a-input v-model:value="userSearch.username" placeholder="请输入用户名" allow-clear @keyup.enter="searchUsers" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="userSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="active">启用</a-select-option>
                <a-select-option value="disabled">禁用</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchUsers">搜索</a-button>
              <a-button @click="resetUserSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="users">
            <a-table-column data-index="username" title="用户名" />
            <a-table-column data-index="real_name" title="姓名" />
            <a-table-column data-index="role" title="角色" />
            <a-table-column title="状态">
              <template #default="{ record: row }">
                <a-tag :color="row.status === 'active' ? 'success' : 'warning'">
                  {{ statusText(row.status) }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" width="220" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditUserDialog(row)">编辑</a-button>
                  <a-button
                    size="small"
                    :type="row.status === 'active' ? 'default' : 'primary'"
                    @click="toggleUserStatus(row)"
                  >
                    {{ row.status === 'active' ? '禁用' : '启用' }}
                  </a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="userPagination.page"
              :page-size="userPagination.pageSize"
              :total="userPagination.total"
              @change="changeUserPage"
            />
          </div>

          <a-modal v-model:open="createUserDialogVisible" title="创建账号" width="420px" @after-close="resetUserForm">
            <a-form layout="vertical" @submit.prevent="createUser">
              <a-form-item label="用户名">
                <a-input v-model:value="userForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="姓名">
                <a-input v-model:value="userForm.real_name" placeholder="请输入姓名" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateUser">取消</a-button>
              <a-button type="primary" @click="createUser">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editUserDialogVisible" title="编辑账号" width="420px" @after-close="resetEditUserForm">
            <a-form layout="vertical" @submit.prevent="updateUser">
              <a-form-item label="用户名">
                <a-input v-model:value="editUserForm.username" placeholder="请输入用户名" />
              </a-form-item>
              <a-form-item label="姓名">
                <a-input v-model:value="editUserForm.real_name" placeholder="请输入姓名" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditUser">取消</a-button>
              <a-button type="primary" @click="updateUser">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'projects'" class="page-view">
          <div class="toolbar"><h2>项目管理</h2><a-button type="primary" @click="openCreateProjectDialog"><template #icon><PlusOutlined /></template>创建项目</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目名称">
              <a-input v-model:value="projectSearch.name" placeholder="请输入项目名称" allow-clear @keyup.enter="searchProjects" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchProjects">搜索</a-button>
              <a-button @click="resetProjectSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="projectList">
            <a-table-column data-index="name" title="项目" />
            <a-table-column data-index="description" title="描述" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditProjectDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteProject(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="projectPagination.page"
              :page-size="projectPagination.pageSize"
              :total="projectPagination.total"
              @change="changeProjectPage"
            />
          </div>

          <a-modal v-model:open="createProjectDialogVisible" title="创建项目" width="420px" @after-close="resetProjectForm">
            <a-form layout="vertical" @submit.prevent="createProject">
              <a-form-item label="项目名称">
                <a-input v-model:value="projectForm.name" placeholder="请输入项目名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-input v-model:value="projectForm.description" placeholder="请输入描述" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateProject">取消</a-button>
              <a-button type="primary" @click="createProject">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editProjectDialogVisible" title="编辑项目" width="420px" @after-close="resetEditProjectForm">
            <a-form layout="vertical" @submit.prevent="updateProject">
              <a-form-item label="项目名称">
                <a-input v-model:value="editProjectForm.name" placeholder="请输入项目名称" />
              </a-form-item>
              <a-form-item label="描述">
                <a-input v-model:value="editProjectForm.description" placeholder="请输入描述" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditProject">取消</a-button>
              <a-button type="primary" @click="updateProject">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'environments'" class="page-view">
          <div class="toolbar"><h2>环境管理</h2><a-button type="primary" @click="openCreateEnvironmentDialog"><template #icon><PlusOutlined /></template>新增环境</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="environmentSearch.project_id" placeholder="请选择项目" allow-clear>
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="环境名称">
              <a-input v-model:value="environmentSearch.name" placeholder="请输入环境名称" allow-clear @keyup.enter="searchEnvironments" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchEnvironments">搜索</a-button>
              <a-button @click="resetEnvironmentSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="environmentList">
            <a-table-column data-index="project_name" title="项目" />
            <a-table-column data-index="name" title="环境名称" />
            <a-table-column data-index="protocol" title="协议" />
            <a-table-column data-index="base_url" title="Base URL" />
            <a-table-column data-index="port" title="端口号" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditEnvironmentDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteEnvironment(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="environmentPagination.page"
              :page-size="environmentPagination.pageSize"
              :total="environmentPagination.total"
              @change="changeEnvironmentPage"
            />
          </div>

          <a-modal v-model:open="createEnvironmentDialogVisible" title="新增环境" width="420px" @after-close="resetEnvironmentForm">
            <a-form layout="vertical" @submit.prevent="createEnvironment">
              <a-form-item label="项目">
                <a-select v-model:value="envForm.project_id" placeholder="请选择项目">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境名称">
                <a-input v-model:value="envForm.name" placeholder="请输入环境名称" />
              </a-form-item>
              <a-form-item label="协议">
                <a-select v-model:value="envForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(envForm.protocol)">
                <a-select-option value="http">http</a-select-option>
                <a-select-option value="https">https</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Base URL">
                <a-input v-model:value="envForm.base_url" placeholder="请输入 Base URL" />
              </a-form-item>
              <a-form-item label="端口号">
                <a-input v-model:value="envForm.port" placeholder="请输入端口号" @input="envForm.port = digitsOnly(envForm.port)" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelCreateEnvironment">取消</a-button>
              <a-button type="primary" @click="createEnvironment">确认</a-button>
            </template>
          </a-modal>

          <a-modal v-model:open="editEnvironmentDialogVisible" title="编辑环境" width="420px" @after-close="resetEditEnvironmentForm">
            <a-form layout="vertical" @submit.prevent="updateEnvironment">
              <a-form-item label="项目">
                <a-select v-model:value="editEnvironmentForm.project_id" placeholder="请选择项目">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="环境名称">
                <a-input v-model:value="editEnvironmentForm.name" placeholder="请输入环境名称" />
              </a-form-item>
              <a-form-item label="协议">
                <a-select v-model:value="editEnvironmentForm.protocol" placeholder="请选择协议" @blur="validateEnvironmentProtocol(editEnvironmentForm.protocol)">
                  <a-select-option value="http">http</a-select-option>
                  <a-select-option value="https">https</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Base URL">
                <a-input v-model:value="editEnvironmentForm.base_url" placeholder="请输入 Base URL" />
              </a-form-item>
              <a-form-item label="端口号">
                <a-input v-model:value="editEnvironmentForm.port" placeholder="请输入端口号" @input="editEnvironmentForm.port = digitsOnly(editEnvironmentForm.port)" />
              </a-form-item>
            </a-form>
            <template #footer>
              <a-button @click="cancelEditEnvironment">取消</a-button>
              <a-button type="primary" @click="updateEnvironment">确认</a-button>
            </template>
          </a-modal>
        </section>

        <section v-if="active === 'apis'" class="page-view">
          <div class="toolbar"><h2>接口管理</h2><a-button type="primary" @click="openCreateApiDialog"><template #icon><PlusOutlined /></template>新增接口</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="apiSearch.project_id" placeholder="请选择项目" allow-clear>
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="名称">
              <a-input v-model:value="apiSearch.name" placeholder="请输入接口名称" allow-clear @keyup.enter="searchApis" />
            </a-form-item>
            <a-form-item label="URL名称">
              <a-input v-model:value="apiSearch.url" placeholder="请输入接口路径" allow-clear @keyup.enter="searchApis" />
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchApis">搜索</a-button>
              <a-button @click="resetApiSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="apiList">
            <a-table-column data-index="project_name" title="项目" />
            <a-table-column data-index="name" title="名称" />
            <a-table-column data-index="description" title="接口描述" />
            <a-table-column data-index="method" title="方法" width="100" />
            <a-table-column data-index="path" title="路径" />
            <a-table-column data-index="create_date" title="创建时间" width="170" />
            <a-table-column data-index="update_date" title="更新时间" width="170" />
            <a-table-column title="操作" width="190" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openEditApiDialog(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteApi(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="apiPagination.page"
              :page-size="apiPagination.pageSize"
              :total="apiPagination.total"
              @change="changeApiPage"
            />
          </div>

        </section>

        <section v-if="activeApiEditor" class="api-editor-page">
          <div class="toolbar">
            <h2>{{ activeApiEditor.label }}</h2>
            <div class="toolbar-actions">
              <a-button @click="closeApiEditorFromPage(activeApiEditor)">关闭</a-button>
              <a-button type="primary" @click="saveApiEditor(activeApiEditor)">保存</a-button>
            </div>
          </div>

          <div class="editor-section">
            <h3>基础信息</h3>
            <a-form layout="vertical" class="form-grid">
              <a-form-item label="项目">
                <a-select
                  v-model:value="activeApiEditor.project_id"
                  placeholder="请选择项目"
                  @change="changeApiEditorProject(activeApiEditor)"
                >
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="名称">
                <a-input v-model:value="activeApiEditor.name" placeholder="请输入接口名称" @input="markApiEditorDirty(activeApiEditor)" />
              </a-form-item>
              <a-form-item label="接口描述" class="wide">
                <a-textarea v-model:value="activeApiEditor.description" :rows="3" placeholder="请输入接口描述" @input="markApiEditorDirty(activeApiEditor)" />
              </a-form-item>
            </a-form>
          </div>

          <div class="editor-section">
            <h3>接口信息</h3>
            <div class="request-line">
              <a-select v-model:value="activeApiEditor.method" placeholder="方法" class="method-select" @change="markApiEditorDirty(activeApiEditor)">
                <a-select-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-select-option>
              </a-select>
              <a-input v-model:value="activeApiEditor.path" placeholder="请输入接口路径 URL，例如 /users" @input="changeApiEditorPath(activeApiEditor)" />
            </div>

            <a-tabs v-model:active-key="activeApiEditor.activePanel" class="api-info-tabs">
              <a-tab-pane tab="URL参数" key="query">
                <div class="kv-title">
                  <h4>URL参数</h4>
                  <a-button size="small" @click="addApiEditorRow(activeApiEditor.queryRows)">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="activeApiEditor.queryRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="key" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeApiEditorRow(activeApiEditor.queryRows, $index, activeApiEditor)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </a-tab-pane>

              <a-tab-pane tab="请求头Header" key="headers">
                <div class="kv-title">
                  <h4>请求头Header</h4>
                  <a-button size="small" @click="addApiEditorRow(activeApiEditor.headerRows)">添加</a-button>
                </div>
                <a-table :pagination="false" :data-source="activeApiEditor.headerRows">
                  <a-table-column title="Key">
                    <template #default="{ record: row }"><a-input v-model:value="row.key" placeholder="Authorization / Content-Type" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="Value">
                    <template #default="{ record: row }"><a-input v-model:value="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </a-table-column>
                  <a-table-column title="操作" width="90">
                    <template #default="{ index: $index }"><a-button size="small" danger @click="removeApiEditorRow(activeApiEditor.headerRows, $index, activeApiEditor)">删除</a-button></template>
                  </a-table-column>
                </a-table>
              </a-tab-pane>

              <a-tab-pane tab="鉴权" key="auth">
                <div class="auth-panel">
                  <div class="auth-sidebar">
                    <a-form layout="vertical">
                      <a-form-item label="鉴权类型">
                        <a-select v-model:value="activeApiEditor.auth.type" @change="changeApiAuthType(activeApiEditor)">
                          <a-select-option value="none">无鉴权</a-select-option>
                          <a-select-option value="bearer">Bearer Token</a-select-option>
                          <a-select-option value="basic">Basic 鉴权</a-select-option>
                          <a-select-option value="api_key">API Key</a-select-option>
                          <a-select-option value="oauth2_client_credentials">OAuth 2.0</a-select-option>
                        </a-select>
                      </a-form-item>
                      <a-form-item label="鉴权数据添加到">
                        <a-select v-model:value="activeApiEditor.auth.addTo" @change="markApiEditorDirty(activeApiEditor)">
                          <a-select-option value="headers">请求头 Header</a-select-option>
                          <a-select-option value="query">URL 参数</a-select-option>
                        </a-select>
                      </a-form-item>
                    </a-form>
                  </div>
                  <div class="auth-main">
                    <a-empty v-if="activeApiEditor.auth.type === 'none'" description="当前接口不启用鉴权" />
                    <a-form v-else layout="vertical" class="auth-form-grid">
                      <template v-if="activeApiEditor.auth.type === 'bearer'">
                        <a-form-item label="请求头名称">
                          <a-input v-model:value="activeApiEditor.auth.headerName" placeholder="Authorization" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="请求头前缀">
                          <a-input v-model:value="activeApiEditor.auth.headerPrefix" placeholder="Bearer" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Token" class="wide">
                          <a-input-password v-model:value="activeApiEditor.auth.token" placeholder="${token} / token" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else-if="activeApiEditor.auth.type === 'basic'">
                        <a-form-item label="用户名">
                          <a-input v-model:value="activeApiEditor.auth.username" placeholder="${username}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="密码">
                          <a-input-password v-model:value="activeApiEditor.auth.password" placeholder="${password}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else-if="activeApiEditor.auth.type === 'api_key'">
                        <a-form-item label="Key">
                          <a-input v-model:value="activeApiEditor.auth.apiKeyName" placeholder="x-api-key" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Value">
                          <a-input-password v-model:value="activeApiEditor.auth.apiKeyValue" placeholder="${api_key}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                      </template>
                      <template v-else>
                        <div class="wide auth-token-box">
                          <h4>当前 Token</h4>
                          <a-form-item label="Access Token">
                            <a-input v-model:value="activeApiEditor.auth.currentToken" readonly placeholder="获取后显示 Access Token" />
                          </a-form-item>
                          <a-form-item label="请求头前缀">
                            <a-input v-model:value="activeApiEditor.auth.headerPrefix" placeholder="Bearer" @input="markApiEditorDirty(activeApiEditor)" />
                          </a-form-item>
                        </div>
                        <div class="wide auth-section-title">
                          <h4>配置新 Token</h4>
                          <a-button size="small" @click="generateApiAuthUrls(activeApiEditor, true)">一键生成 URL/Scope</a-button>
                        </div>
                        <a-form-item label="授权模式">
                          <a-select value="client_credentials" disabled>
                            <a-select-option value="client_credentials">Client Credentials</a-select-option>
                          </a-select>
                        </a-form-item>
                        <a-form-item label="Access Token URL" class="wide">
                          <a-input v-model:value="activeApiEditor.auth.tokenUrl" placeholder="环境地址 + /OAuth/Oauth/Token" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Client ID">
                          <a-input v-model:value="activeApiEditor.auth.clientId" placeholder="KSTAPI / ${client_id}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Client Secret">
                          <a-input-password v-model:value="activeApiEditor.auth.clientSecret" placeholder="1234 / ${client_secret}" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="Scope" class="wide">
                          <a-input v-model:value="activeApiEditor.auth.scope" placeholder="默认当前环境地址 + 接口路径" @input="markApiEditorDirty(activeApiEditor)" />
                        </a-form-item>
                        <a-form-item label="客户端认证方式" class="wide">
                          <a-select v-model:value="activeApiEditor.auth.clientAuthentication" @change="markApiEditorDirty(activeApiEditor)">
                            <a-select-option value="body">在请求体中发送 Client ID/Secret</a-select-option>
                            <a-select-option value="basic">通过 Basic Auth 请求头发送</a-select-option>
                          </a-select>
                        </a-form-item>
                        <div class="wide">
                          <a-button type="primary" :loading="activeApiEditor.auth.loading" @click="getApiEditorAccessToken(activeApiEditor)">获取 Access Token</a-button>
                        </div>
                      </template>
                    </a-form>
                  </div>
                </div>
              </a-tab-pane>

              <a-tab-pane tab="请求Body" key="body">
                <div class="body-format-row">
                  <span>Body格式</span>
                  <a-radio-group v-model:value="activeApiEditor.bodyFormat" @change="changeApiEditorBodyFormat(activeApiEditor)">
                    <a-radio-button value="json">json</a-radio-button>
                    <a-radio-button value="xml">xml</a-radio-button>
                    <a-radio-button value="x-www-form-data">x-www-form-data</a-radio-button>
                  </a-radio-group>
                </div>
              </a-tab-pane>
              <a-tab-pane tab="Pre-script" key="pre-script">
                <a-textarea
                  v-model:value="activeApiEditor.preScript"
                  :rows="14"
                  class="pre-script-input"
                  placeholder="pm.environment.set('timestamp', Date.now());&#10;pm.environment.set('sign', CryptoJS.MD5(pm.environment.get('timestamp')).toString());"
                  @input="markApiEditorDirty(activeApiEditor)"
                />
                <p class="pre-script-hint">
                  支持 pm.environment.get/set、Date、Math、JSON、CryptoJS.MD5/SHA256 和 console.log/info/warn；不支持 require、网络请求、文件或数据库访问。
                </p>
              </a-tab-pane>
              <a-tab-pane tab="加密配置" key="encryption">
                <a-form layout="vertical">
                  <a-form-item label="启用接口加密">
                    <a-switch v-model:checked="activeApiEditor.encryption.enabled" @change="markApiEditorDirty(activeApiEditor)" />
                  </a-form-item>
                  <template v-if="activeApiEditor.encryption.enabled">
                    <a-form-item label="加密方式">
                      <a-select v-model:value="activeApiEditor.encryption.mode" @change="markApiEditorDirty(activeApiEditor)">
                        <a-select-option value="rsa_aes_sm3">RSA-AES-SM3</a-select-option>
                      </a-select>
                    </a-form-item>
                    <a-form-item label="处理方式">
                      <a-checkbox v-model:checked="activeApiEditor.encryption.encryptRequest" @change="markApiEditorDirty(activeApiEditor)">请求 Body 加密</a-checkbox>
                      <a-checkbox v-model:checked="activeApiEditor.encryption.decryptResponse" @change="markApiEditorDirty(activeApiEditor)">响应 Body 解密</a-checkbox>
                    </a-form-item>
                    <p class="pre-script-hint">平台使用服务器预置的固定 RSA 密钥，无需上传 PEM 文件。</p>
                  </template>
                </a-form>
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>

        <section v-if="active === 'cases'" class="page-view">
          <div class="toolbar"><h2>用例管理</h2><a-button type="primary" @click="openCreateCasePage"><template #icon><PlusOutlined /></template>新增用例</a-button></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="项目">
              <a-select v-model:value="caseSearch.project_id" placeholder="请选择项目" allow-clear @change="changeCaseSearchProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="接口">
              <a-select v-model:value="caseSearch.api_id" placeholder="请先选择项目" allow-clear :disabled="!caseSearch.project_id">
                <a-select-option v-for="a in caseSearchApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchCases">搜索</a-button>
              <a-button @click="resetCaseSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="caseList">
            <a-table-column title="编号" width="80">
              <template #default="{ index: $index }">{{ caseSerialNumber($index) }}</template>
            </a-table-column>
            <a-table-column data-index="project_name" title="项目" />
            <a-table-column data-index="api_name" title="接口" />
            <a-table-column data-index="name" title="用例名称" />
            <a-table-column title="操作" width="270" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openCaseDetailDialog(row)">查看</a-button>
                  <a-button size="small" @click="openEditCasePage(row)">编辑</a-button>
                  <a-button size="small" danger @click="deleteCase(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="casePagination.page"
              :page-size="casePagination.pageSize"
              :total="casePagination.total"
              @change="changeCasePage"
            />
          </div>
        </section>

        <section v-if="active === 'case-create' || active.startsWith('case-edit-')">
          <div class="toolbar">
            <h2>{{ caseForm.id ? '编辑用例' : '新增用例' }}</h2>
            <div class="toolbar-actions">
              <a-button @click="closeCaseEditorPage">关闭</a-button>
              <a-button type="primary" @click="saveCase">保存</a-button>
            </div>
          </div>
          <a-form layout="vertical" class="form-grid">
            <a-form-item label="项目">
              <a-select v-model:value="caseForm.project_id" placeholder="请选择项目" @change="changeCaseFormProject">
                <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="接口">
              <a-select v-model:value="caseForm.api_id" placeholder="请先选择项目" :disabled="!caseForm.project_id">
                <a-select-option v-for="a in caseFormApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input v-model:value="caseForm.name" placeholder="请输入用例名称" />
            </a-form-item>
            <a-form-item label="用例描述" class="wide">
              <a-textarea v-model:value="caseForm.description" :rows="3" placeholder="请输入用例描述" />
            </a-form-item>
            <a-form-item label="Body" class="wide">
              <a-textarea v-model:value="caseForm.bodyText" :rows="8" placeholder="请输入 JSON Body" />
              <p class="form-help-text">可直接引用上游提取变量，例如 ${token}、${userId}，测试计划按队列顺序执行时会自动替换。</p>
            </a-form-item>
            <div class="wide">
              <div class="kv-title">
                <h4>响应提取 / 参数关联</h4>
                <a-button size="small" @click="addCaseExtractorRow">添加</a-button>
              </div>
              <a-table :pagination="false" :data-source="caseForm.extractorRows">
                <a-table-column title="变量名" width="220">
                  <template #default="{ record: row }"><a-input v-model:value="row.name" placeholder="token" /></template>
                </a-table-column>
                <a-table-column title="JSONPath">
                  <template #default="{ record: row }"><a-input v-model:value="row.path" placeholder="$.data.token" /></template>
                </a-table-column>
                <a-table-column title="操作" width="90">
                  <template #default="{ index: $index }"><a-button size="small" danger @click="removeCaseExtractorRow($index)">删除</a-button></template>
                </a-table-column>
              </a-table>
              <p class="form-help-text">提取成功后，后续用例可在 Body 中使用 ${变量名} 引用。</p>
            </div>
            <div class="wide">
              <div class="kv-title">
                <h4>断言</h4>
                <a-button size="small" @click="addCaseAssertionRow">添加</a-button>
              </div>
              <a-table :pagination="false" :data-source="caseForm.assertionRows">
                <a-table-column title="断言类型" width="190">
                  <template #default="{ record: row }">
                    <a-select v-model:value="row.type">
                      <a-select-option v-for="option in assertionTypes" :key="option.value" :value="option.value">{{ option.label }}</a-select-option>
                    </a-select>
                  </template>
                </a-table-column>
                <a-table-column title="JSONPath/路径">
                  <template #default="{ record: row }"><a-input v-model:value="row.path" placeholder="$.data.id / status_code" /></template>
                </a-table-column>
                <a-table-column title="操作符" width="120">
                  <template #default="{ record: row }"><a-input v-model:value="row.operator" placeholder="==" /></template>
                </a-table-column>
                <a-table-column title="期望值">
                  <template #default="{ record: row }"><a-input v-model:value="row.expected" placeholder="200 / success" /></template>
                </a-table-column>
                <a-table-column title="操作" width="90">
                  <template #default="{ index: $index }"><a-button size="small" danger @click="removeCaseAssertionRow($index)">删除</a-button></template>
                </a-table-column>
              </a-table>
            </div>
          </a-form>
        </section>

        <a-modal v-model:open="caseBodyDialogVisible" title="请求 Body" width="640px">
          <a-textarea v-model:value="caseBodyPreview" :rows="16" readonly />
          <template #footer>
            <a-button type="primary" @click="caseBodyDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <section v-if="active === 'execute'" class="plan-page">
          <div class="plan-page-header plan-workbench-header">
            <div>
              <h2>测试计划</h2>
              <p>编排回归范围，统一查看执行状态与最新结果。</p>
            </div>
              <a-button type="primary" @click="openCreatePlanPage"><template #icon><PlusOutlined /></template>新建测试计划</a-button>
          </div>
          <div class="plan-search-panel plan-filter-bar">
            <a-form class="search-form plan-search-form" layout="inline">
              <a-form-item label="计划名称">
                <a-input v-model:value="planSearch.name" placeholder="请输入计划名称" allow-clear @keyup.enter="searchPlans" />
              </a-form-item>
              <a-form-item label="项目">
                <a-select v-model:value="planSearch.project_id" placeholder="请选择项目" allow-clear @change="changePlanSearchProject">
                  <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="包含接口">
                <a-select v-model:value="planSearch.api_id" placeholder="请先选择项目" allow-clear :disabled="!planSearch.project_id">
                <a-select-option v-for="a in planSearchApis" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
                </a-select>
              </a-form-item>
              <div class="search-actions">
                <a-button type="primary" @click="searchPlans">查询</a-button>
                <a-button @click="resetPlanSearch">重置</a-button>
              </div>
            </a-form>
          </div>
          <div class="plan-table-panel plan-data-surface">
            <div class="plan-table-heading plan-list-toolbar">
              <div>
                <h3>全部计划</h3>
                <span>共 {{ planPagination.total }} 条记录</span>
              </div>
              <span class="plan-list-hint">点击计划名称可查看执行范围</span>
            </div>
          <a-table :pagination="false" :data-source="planList" row-key="id" :scroll="{ x: 1360 }" class="plan-list-table">
            <template #expandedRowRender="{ record: row }">
              <div class="plan-case-expand-list">
                <div class="plan-case-expand-head">
                  <span>用例名称</span>
                  <span>接口</span>
                  <span>状态</span>
                  <span>操作</span>
                </div>
                <div v-for="caseRow in row.cases || []" :key="caseRow.id" class="plan-case-expand-row">
                  <span class="plan-case-expand-name">{{ caseRow.name || '-' }}</span>
                  <span class="plan-case-expand-api">{{ caseRow.api_name || '-' }}</span>
                  <span><a-tag :color="executionStatusColor(caseRow.status)">{{ executionStatusText(caseRow.status) }}</a-tag></span>
                  <span class="plan-case-expand-action">
                    <a-button size="small" @click="openCaseDetailDialog(caseRow, row.environment_id, row.last_execution_id)">查看</a-button>
                  </span>
                </div>
                <a-empty v-if="!(row.cases || []).length" description="暂无用例" :image-style="{ width: '48px', height: '48px' }" />
              </div>
            </template>
            <a-table-column data-index="name" title="计划名称" width="280" class-name="plan-wrap-cell" />
            <a-table-column data-index="project_name" title="项目" width="220" class-name="plan-wrap-cell" />
            <a-table-column data-index="environment_name" title="环境" width="220" class-name="plan-wrap-cell" />
            <a-table-column data-index="api_name" title="包含接口" width="260" class-name="plan-wrap-cell" />
            <a-table-column title="状态" width="96" align="center">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.last_status)">{{ executionStatusText(row.last_status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行时间" width="150">
              <template #default="{ record: row }">{{ formatMinute(row.last_executed_at) }}</template>
            </a-table-column>
            <a-table-column title="操作" width="240" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" type="primary" @click="executePlan(row)">执行</a-button>
                  <a-button size="small" type="link" @click="openEditPlanPage(row)">编辑</a-button>
                  <a-button size="small" type="link" @click="openExecutionDetail(row)">进度</a-button>
                  <a-button size="small" type="link" danger @click="deletePlan(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="planPagination.page"
              :page-size="planPagination.pageSize"
              :total="planPagination.total"
              @change="changePlanPage"
            />
          </div>
          </div>
        </section>

        <section v-if="activePlanEditor" class="plan-editor-page">
          <div class="plan-editor-header plan-editor-titlebar">
            <div>
              <h2>{{ activePlanEditor.label }}</h2>
              <p>{{ activePlanEditor.dirty ? '存在未保存的更改' : '所有更改已保存' }}</p>
            </div>
          </div>

          <div class="plan-editor-workspace">
            <aside class="plan-editor-rail" aria-label="计划配置步骤">
              <div class="plan-editor-rail-title">配置步骤</div>
              <div class="plan-editor-step is-active"><span>01</span><div><strong>基础配置</strong><small>项目、环境与接口</small></div></div>
              <div class="plan-editor-step"><span>02</span><div><strong>选择用例</strong><small>筛选并加入执行范围</small></div></div>
              <div class="plan-editor-step"><span>03</span><div><strong>执行编排</strong><small>调整用例执行顺序</small></div></div>
            </aside>

            <div class="plan-editor-content">
              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading">
                  <div>
                    <span class="plan-section-index">01</span>
                    <h3>基础配置</h3>
                    <p>选择目标项目、执行环境和需要覆盖的接口。</p>
                  </div>
                </div>
                <a-form layout="vertical" class="form-grid">
                  <a-form-item label="项目">
                    <a-select v-model:value="activePlanEditor.project_id" placeholder="请选择项目" @change="changePlanEditorProject(activePlanEditor)">
                      <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="环境">
                    <a-select v-model:value="activePlanEditor.environment_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="markPlanEditorDirty(activePlanEditor)">
                      <a-select-option v-for="e in planEditorEnvironments(activePlanEditor)" :key="e.id" :value="e.id">{{ e.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="接口">
                    <a-select v-model:value="activePlanEditor.api_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="changePlanEditorApi(activePlanEditor)">
                      <a-select-option v-for="a in planEditorApis(activePlanEditor)" :key="a.id" :value="a.id">{{ a.name }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="测试计划名称">
                    <a-input v-model:value="activePlanEditor.name" placeholder="请输入测试计划名称" @input="markPlanEditorDirty(activePlanEditor)" />
                  </a-form-item>
                </a-form>
              </div>

              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading plan-section-heading-actions">
                  <div>
                    <span class="plan-section-index">02</span>
                    <h3>选择测试用例</h3>
                    <p>查询后勾选用例，并添加到下方执行队列。</p>
                  </div>
                  <div class="toolbar-actions">
                    <a-button @click="loadPlanCandidateCases(activePlanEditor)">刷新列表</a-button>
                    <a-button type="primary" @click="addSelectedPlanCases(activePlanEditor)">加入队列</a-button>
                  </div>
                </div>
                <a-table :pagination="false"
                  :data-source="activePlanEditor.candidateCases"
                  size="small"
                  row-key="id"
                  :row-selection="{ onChange: (_keys: any[], rows: any[]) => changePlanCandidateSelection(activePlanEditor, rows) }"
                >
                  <a-table-column data-index="name" title="用例名称" />
                  <a-table-column data-index="api_name" title="接口" />
                  <a-table-column title="操作" width="100">
                    <template #default="{ record: row }">
                      <a-button size="small" type="link" @click="openCaseDetailDialog(row, activePlanEditor.environment_id)">查看</a-button>
                    </template>
                  </a-table-column>
                </a-table>
              </div>

              <div class="editor-section plan-editor-section">
                <div class="plan-section-heading">
                  <div>
                    <span class="plan-section-index">03</span>
                    <h3>执行队列</h3>
                    <p>拖动用例调整执行顺序。</p>
                  </div>
                  <span class="plan-queue-count">{{ activePlanEditor.queue.length }} 个用例</span>
                </div>
                <div class="plan-queue">
                  <div
                    v-for="(item, index) in activePlanEditor.queue"
                    :key="item.id"
                    class="plan-queue-row"
                    draggable="true"
                    @dragstart="startPlanQueueDrag(activePlanEditor, index)"
                    @dragover.prevent
                    @drop="dropPlanQueueRow(activePlanEditor, index)"
                  >
                    <span class="drag-handle">⋮⋮</span>
                    <span class="queue-name">{{ item.name }}</span>
                    <span class="queue-api">{{ item.api_name || '-' }}</span>
                    <a-button size="small" type="link" @click="openCaseDetailDialog(item, activePlanEditor.environment_id)">查看</a-button>
                    <a-button size="small" type="link" danger @click="removePlanQueueCase(activePlanEditor, index)">移除</a-button>
                  </div>
                  <a-empty v-if="activePlanEditor.queue.length === 0" description="暂无用例" />
                </div>
              </div>
            </div>
          </div>
          <div class="plan-editor-footer">
            <span>{{ activePlanEditor.dirty ? '当前内容尚未保存' : '已保存' }}</span>
            <div class="toolbar-actions">
              <a-button @click="closePlanEditorFromPage(activePlanEditor)">取消</a-button>
              <a-button type="primary" @click="savePlanEditor(activePlanEditor, true)">保存测试计划</a-button>
            </div>
          </div>
        </section>

        <a-modal v-model:open="caseDetailDialogVisible" title="用例详情" width="760px">
          <div class="detail-grid">
            <strong>请求方法</strong><span>{{ caseDetail.method || '-' }}</span>
            <strong>URL</strong><span>{{ caseDetail.url || '-' }}</span>
            <strong>请求头</strong><pre>{{ formatJson(caseDetail.request_headers) }}</pre>
            <template v-if="caseDetail.request_body_original !== undefined">
              <strong>请求原文</strong><pre>{{ formatJson(caseDetail.request_body_original) }}</pre>
              <strong>实际请求密文</strong><pre>{{ formatJson(caseDetail.request_body) }}</pre>
            </template>
            <template v-else>
              <strong>请求体</strong><pre>{{ formatJson(caseDetail.request_body) }}</pre>
            </template>
            <strong>断言信息</strong><pre>{{ formatJson(caseDetail.assertions) }}</pre>
            <strong>提取规则</strong><pre>{{ formatJson(caseDetail.extractors) }}</pre>
            <template v-if="caseDetail.extracted_variables?.length">
              <strong>本次提取值</strong><pre>{{ formatJson(caseDetail.extracted_variables) }}</pre>
            </template>
            <template v-if="caseDetail.response_snapshot?.decrypted_text !== undefined">
              <strong>响应密文</strong><pre>{{ formatJson(caseDetail.response_snapshot.encrypted_json) }}</pre>
              <strong>响应解密内容</strong><pre>{{ caseDetail.response_snapshot.decrypted_text }}</pre>
            </template>
            <template v-else>
              <strong>返回报文</strong><pre>{{ formatJson(caseDetail.response_snapshot) }}</pre>
            </template>
          </div>
          <template #footer>
            <a-button type="primary" @click="caseDetailDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <a-modal v-model:open="executionDetailDialogVisible" title="执行进度" width="820px">
          <a-descriptions v-if="executionDetail.task" :column="3" border>
            <a-descriptions-item label="状态">{{ executionDetail.task.status }}</a-descriptions-item>
            <a-descriptions-item label="汇总">{{ formatJson(executionDetail.task.summary) }}</a-descriptions-item>
          </a-descriptions>
          <a-table :pagination="false" :data-source="executionDetail.results" size="small" class="sub">
            <template #expandedRowRender="{ record: row }">
              <div class="execution-result-expand">
                <strong>参数提取结果</strong>
                <pre>{{ formatJson(row.response_snapshot?.extracted_variables || []) }}</pre>
                <strong>请求快照</strong>
                <pre>{{ formatJson(row.request_snapshot) }}</pre>
                <strong>响应快照</strong>
                <pre>{{ formatJson(row.response_snapshot) }}</pre>
              </div>
            </template>
            <a-table-column data-index="case_name" title="用例名称" width="180" />
            <a-table-column data-index="api_name" title="接口" width="180" />
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column data-index="duration_ms" title="耗时(ms)" width="110" />
            <a-table-column data-index="error_message" title="错误信息" />
          </a-table>
          <template #footer>
            <a-button type="primary" @click="executionDetailDialogVisible = false">关闭</a-button>
          </template>
        </a-modal>

        <section v-if="active === 'reports'" class="page-view">
          <div class="toolbar"><h2>报告中心</h2></div>
          <a-form class="search-form" layout="vertical">
            <a-form-item label="测试计划名称">
              <a-input v-model:value="reportSearch.name" placeholder="请输入测试计划名称" allow-clear @keyup.enter="searchReports" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model:value="reportSearch.status" placeholder="请选择状态" allow-clear>
                <a-select-option value="queued">排队中</a-select-option>
                <a-select-option value="running">执行中</a-select-option>
                <a-select-option value="passed">已通过</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
                <a-select-option value="error">异常</a-select-option>
              </a-select>
            </a-form-item>
            <div class="search-actions">
              <a-button type="primary" @click="searchReports">搜索</a-button>
              <a-button @click="resetReportSearch">重置</a-button>
            </div>
          </a-form>
          <a-table :pagination="false" :data-source="reportList">
            <a-table-column data-index="target_name" title="测试计划名称" width="180" />
            <a-table-column data-index="project_name" title="项目" />
            <a-table-column data-index="environment_name" title="环境" />
            <a-table-column title="状态" width="100">
              <template #default="{ record: row }">
                <a-tag :color="executionStatusColor(row.status)">{{ executionStatusText(row.status) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="执行时间" width="150">
              <template #default="{ record: row }">{{ formatMinute(row.ended_at || row.started_at || row.create_date) }}</template>
            </a-table-column>
            <a-table-column data-index="executor_name" title="执行用户" width="120" />
            <a-table-column title="操作" width="230" fixed="right">
              <template #default="{ record: row }">
                <div class="table-actions">
                  <a-button size="small" @click="openReport(row)">查看报告</a-button>
                  <a-button size="small" danger @click="deleteReport(row)">删除</a-button>
                </div>
              </template>
            </a-table-column>
          </a-table>
          <div class="pagination">
            <a-pagination
              :show-total="paginationTotal"
              show-less-items
              :current="reportPagination.page"
              :page-size="reportPagination.pageSize"
              :total="reportPagination.total"
              @change="changeReportPage"
            />
          </div>
        </section>

        <section v-if="active === 'logs'" class="page-view">
          <h2>日志中心</h2>
          <a-table :pagination="false" :data-source="logs"><a-table-column data-index="module" title="模块" /><a-table-column data-index="action" title="操作" /><a-table-column data-index="result" title="结果" /><a-table-column data-index="create_date" title="时间" /></a-table>
        </section>

        <a-modal v-model:open="changePasswordDialogVisible" title="修改密码" width="420px" @after-close="resetChangePasswordForm">
          <a-form layout="vertical" @submit.prevent="changePassword">
            <a-form-item label="原密码">
              <a-input-password v-model:value="changePasswordForm.old_password" placeholder="请输入原密码" />
            </a-form-item>
            <a-form-item label="新密码">
              <a-input-password
                v-model:value="changePasswordForm.new_password"
                placeholder="请输入新密码"
                @blur="validatePasswordMatch"
              />
            </a-form-item>
            <a-form-item label="确认密码">
              <a-input-password
                v-model:value="changePasswordForm.confirm_password"
                placeholder="请再次输入新密码"
                @blur="validatePasswordMatch"
              />
            </a-form-item>
          </a-form>
          <template #footer>
            <a-button @click="cancelChangePassword">取消</a-button>
            <a-button type="primary" @click="changePassword">确认</a-button>
          </template>
        </a-modal>
      </a-layout-content>
    </a-layout>
  </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import {
  ApiOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  DashboardOutlined,
  DeleteOutlined,
  DownOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  LockOutlined,
  LoginOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  ProfileOutlined,
  ProjectOutlined,
  ReloadOutlined,
  SaveOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
  UserAddOutlined,
  UserOutlined
} from '@ant-design/icons-vue'
import { api, type User } from './api'

const appTheme = {
  token: {
    colorPrimary: '#1677ff',
    colorInfo: '#1677ff',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorBgLayout: '#f5f7fa',
    colorText: '#1f2937',
    colorTextSecondary: '#667085',
    colorBorder: '#e6eaf0',
    borderRadius: 6,
    controlHeight: 34,
    fontSize: 14
  },
  components: {
    Button: { borderRadius: 6, controlHeightSM: 30 },
    Card: { borderRadiusLG: 8 },
    Input: { activeShadow: '0 0 0 2px rgba(22, 119, 255, 0.12)' },
    Select: { optionSelectedBg: '#eef6ff' },
    Table: { headerBg: '#f8fafc', rowHoverBg: '#f5f9ff' }
  }
}

type AppTab = { name: string; label: string; closable: boolean }
type KeyValueRow = { id: number; key: string; value: string }
type CaseAssertionRow = { id: number; type: string; path: string; operator: string; expected: string }
type CaseExtractorRow = { id: number; name: string; path: string }

function confirmAction(
  content: string,
  title: string,
  options: { confirmButtonText?: string; cancelButtonText?: string; type?: string; distinguishCancelAndClose?: boolean } = {}
) {
  return new Promise<void>((resolve, reject) => {
    Modal.confirm({
      title,
      content,
      okText: options.confirmButtonText || '确认',
      cancelText: options.cancelButtonText || '取消',
      onOk: () => resolve(),
      onCancel: () => reject('cancel')
    })
  })
}
type ApiEncryption = {
  enabled: boolean
  mode: 'none' | 'rsa_aes_sm3'
  encryptRequest: boolean
  decryptResponse: boolean
}
type ApiAuth = {
  type: 'none' | 'bearer' | 'basic' | 'api_key' | 'oauth2_client_credentials'
  addTo: 'headers' | 'query'
  headerName: string
  headerPrefix: string
  token: string
  username: string
  password: string
  apiKeyName: string
  apiKeyValue: string
  tokenUrl: string
  clientId: string
  clientSecret: string
  scope: string
  audience: string
  clientAuthentication: 'body' | 'basic'
  currentToken: string
  loading: boolean
}
type ApiEditor = {
  tabName: string
  label: string
  mode: 'create' | 'edit'
  apiId?: number
  project_id?: number
  name: string
  description: string
  method: string
  path: string
  bodyFormat: 'json' | 'xml' | 'x-www-form-data'
  activePanel: '' | 'query' | 'headers' | 'auth' | 'body' | 'pre-script' | 'encryption'
  queryRows: KeyValueRow[]
  headerRows: KeyValueRow[]
  preScript: string
  encryption: ApiEncryption
  auth: ApiAuth
  dirty: boolean
}
type PlanEditor = {
  tabName: string
  label: string
  mode: 'create' | 'edit'
  planId?: number
  project_id?: number
  environment_id?: number
  api_id?: number
  name: string
  candidateCases: any[]
  selectedCases: any[]
  queue: any[]
  dragIndex?: number
  dirty: boolean
}

const menuMeta: Record<string, AppTab> = {
  dashboard: { name: 'dashboard', label: '数据概览', closable: false },
  projects: { name: 'projects', label: '项目管理', closable: true },
  environments: { name: 'environments', label: '环境管理', closable: true },
  apis: { name: 'apis', label: '接口管理', closable: true },
  cases: { name: 'cases', label: '用例管理', closable: true },
  execute: { name: 'execute', label: '测试计划', closable: true },
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
const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)
const isMobile = ref(false)
const loginLoading = ref(false)

const me = ref<User | null>(null)
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const users = ref<any[]>([])
const projects = ref<any[]>([])
const projectList = ref<any[]>([])
const environments = ref<any[]>([])
const environmentList = ref<any[]>([])
const apis = ref<any[]>([])
const apiList = ref<any[]>([])
const cases = ref<any[]>([])
const caseList = ref<any[]>([])
const executions = ref<any[]>([])
const reportList = ref<any[]>([])
const planList = ref<any[]>([])
const logs = ref<any[]>([])
const selectedProject = ref<any>(null)

const loginForm = reactive({ username: '', password: '' })
const userSearch = reactive({ username: '', status: '' })
const userPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const projectSearch = reactive({ name: '' })
const projectPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const environmentSearch = reactive({ project_id: undefined as number | undefined, name: '' })
const environmentPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const apiSearch = reactive({ project_id: undefined as number | undefined, name: '', url: '' })
const apiPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const caseSearch = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined })
const casePagination = reactive({ page: 1, pageSize: 10, total: 0 })
const planSearch = reactive({ project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '' })
const planPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const reportSearch = reactive({ name: '', status: '' })
const reportPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const planExecutionPollers = new Map<number, number>()
const createUserDialogVisible = ref(false)
const editUserDialogVisible = ref(false)
const createProjectDialogVisible = ref(false)
const editProjectDialogVisible = ref(false)
const createEnvironmentDialogVisible = ref(false)
const editEnvironmentDialogVisible = ref(false)
const changePasswordDialogVisible = ref(false)
const caseBodyDialogVisible = ref(false)
const caseDetailDialogVisible = ref(false)
const executionDetailDialogVisible = ref(false)
const caseBodyPreview = ref('')
const caseDetail = reactive<any>({})
const executionDetail = reactive<any>({ task: null, results: [] })
const userForm = reactive({ username: '', real_name: '' })
const editUserForm = reactive({ id: undefined as number | undefined, username: '', real_name: '' })
const changePasswordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const projectForm = reactive({ name: '', description: '' })
const editProjectForm = reactive({ id: undefined as number | undefined, name: '', description: '' })
const envForm = reactive({ project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const editEnvironmentForm = reactive({ id: undefined as number | undefined, project_id: undefined as number | undefined, name: '', protocol: '', base_url: '', port: '' })
const caseForm = reactive({
  id: undefined as number | undefined,
  project_id: undefined as number | undefined,
  api_id: undefined as number | undefined,
  name: '',
  description: '',
  bodyText: '{}',
  assertionRows: [] as CaseAssertionRow[],
  extractorRows: [] as CaseExtractorRow[]
})
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })
const apiEditors = reactive<Record<string, ApiEditor>>({})
const planEditors = reactive<Record<string, PlanEditor>>({})
const avatarText = computed(() => me.value?.username.slice(0, 1).toUpperCase() || 'U')
const activeApiEditor = computed(() => apiEditors[active.value])
const activePlanEditor = computed(() => planEditors[active.value])
const currentPageTitle = computed(() => activeApiEditor.value?.label || activePlanEditor.value?.label || menuMeta[active.value]?.label || '接口测试平台')
const dashboardStats = computed(() => [
  { label: '项目数', value: projects.value.length, description: '已配置项目', tone: 'blue', icon: ProjectOutlined },
  { label: '接口数', value: apis.value.length, description: '已维护接口定义', tone: 'cyan', icon: ApiOutlined },
  { label: '用例数', value: cases.value.length, description: '可用于回归执行', tone: 'green', icon: FileTextOutlined },
  { label: '执行任务', value: executions.value.length, description: '历史执行任务', tone: 'orange', icon: PlayCircleOutlined }
])
const caseSearchApis = computed(() => apis.value.filter(item => caseSearch.project_id && item.project_id === caseSearch.project_id))
const caseFormApis = computed(() => apis.value.filter(item => caseForm.project_id && item.project_id === caseForm.project_id))
const planSearchApis = computed(() => apis.value.filter(item => planSearch.project_id && item.project_id === planSearch.project_id))
const assertionTypes = [
  { label: 'HTTP状态码', value: 'status_code' },
  { label: 'JSONPath等于', value: 'jsonpath_equal' },
  { label: 'JSONPath存在', value: 'jsonpath_exists' },
  { label: 'JSONPath非空', value: 'jsonpath_not_empty' },
  { label: '响应时间小于', value: 'duration_lt' },
  { label: '响应文本包含', value: 'body_contains' }
]
const paginationTotal = (total: number) => `共 ${total} 条`

function parseJson(text: string, fallback: any) {
  try { return JSON.parse(text || '') } catch { return fallback }
}

async function loadAll() {
  const calls = [
    api.get('/projects').then(r => projects.value = r.data),
    api.get('/environments').then(r => environments.value = r.data),
    api.get('/apis').then(r => apis.value = r.data),
    refreshAllCases(),
    api.get('/executions').then(r => executions.value = r.data),
    api.get('/logs').then(r => logs.value = r.data)
  ]
  calls.push(loadUsers())
  calls.push(loadProjects())
  calls.push(loadEnvironments())
  calls.push(loadApis())
  calls.push(loadCases())
  calls.push(loadPlans())
  calls.push(loadReports())
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

async function loadApis() {
  const projectId = apiSearch.project_id
  const name = apiSearch.name.trim()
  const url = apiSearch.url.trim()
  const { data } = await api.get('/apis', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(name ? { name } : {}),
      ...(url ? { url } : {}),
      page: apiPagination.page,
      page_size: apiPagination.pageSize
    }
  })
  apiList.value = data.items
  apiPagination.total = data.total
  apiPagination.page = data.page
  apiPagination.pageSize = data.page_size
}

async function searchApis() {
  apiPagination.page = 1
  await loadApis()
}

async function resetApiSearch() {
  apiSearch.project_id = undefined
  apiSearch.name = ''
  apiSearch.url = ''
  apiPagination.page = 1
  await loadApis()
}

async function changeApiPage(page: number) {
  apiPagination.page = page
  await loadApis()
}

async function loadCases() {
  const projectId = caseSearch.project_id
  const apiId = caseSearch.api_id
  const { data } = await api.get('/cases', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(apiId ? { api_id: apiId } : {}),
      page: casePagination.page,
      page_size: casePagination.pageSize
    }
  })
  caseList.value = data.items
  casePagination.total = data.total
  casePagination.page = data.page
  casePagination.pageSize = data.page_size
}

async function refreshAllCases() {
  const { data } = await api.get('/cases')
  cases.value = data
}

async function searchCases() {
  casePagination.page = 1
  await loadCases()
}

async function resetCaseSearch() {
  caseSearch.project_id = undefined
  caseSearch.api_id = undefined
  casePagination.page = 1
  await loadCases()
}

function changeCaseSearchProject() {
  caseSearch.api_id = undefined
}

async function changeCasePage(page: number) {
  casePagination.page = page
  await loadCases()
}

function caseSerialNumber(index: number) {
  return (casePagination.page - 1) * casePagination.pageSize + index + 1
}

async function loadPlans() {
  const projectId = planSearch.project_id
  const apiId = planSearch.api_id
  const name = planSearch.name.trim()
  const { data } = await api.get('/plans', {
    params: {
      ...(projectId ? { project_id: projectId } : {}),
      ...(apiId ? { api_id: apiId } : {}),
      ...(name ? { name } : {}),
      page: planPagination.page,
      page_size: planPagination.pageSize
    }
  })
  planList.value = data.items
  planPagination.total = data.total
  planPagination.page = data.page
  planPagination.pageSize = data.page_size
}

async function refreshPlansAfterChange() {
  await loadPlans()
}

async function searchPlans() {
  planPagination.page = 1
  await loadPlans()
}

async function resetPlanSearch() {
  planSearch.project_id = undefined
  planSearch.api_id = undefined
  planSearch.name = ''
  planPagination.page = 1
  await loadPlans()
}

function changePlanSearchProject() {
  planSearch.api_id = undefined
}

async function changePlanPage(page: number) {
  planPagination.page = page
  await loadPlans()
}

async function loadReports() {
  const name = reportSearch.name.trim()
  const status = reportSearch.status
  const { data } = await api.get('/executions', {
    params: {
      target_type: 'plan',
      ...(name ? { name } : {}),
      ...(status ? { status } : {}),
      page: reportPagination.page,
      page_size: reportPagination.pageSize
    }
  })
  reportList.value = data.items
  reportPagination.total = data.total
  reportPagination.page = data.page
  reportPagination.pageSize = data.page_size
}

async function searchReports() {
  reportPagination.page = 1
  await loadReports()
}

async function resetReportSearch() {
  reportSearch.name = ''
  reportSearch.status = ''
  reportPagination.page = 1
  await loadReports()
}

async function changeReportPage(page: number) {
  reportPagination.page = page
  await loadReports()
}

async function login() {
  if (loginLoading.value) {
    return
  }
  loginLoading.value = true
  try {
    const { data } = await api.post('/auth/login', loginForm)
    localStorage.setItem('session_token', data.token)
    me.value = data.user
    await loadAll()
  } catch {
    message.error('用户名或密码错误')
  } finally {
    loginLoading.value = false
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

function openRuntimeTab(tab: AppTab) {
  if (!openedTabs.value.some(item => item.name === tab.name)) {
    openedTabs.value.push(tab)
  }
  active.value = tab.name
  saveTabs()
}

function selectMenu(index: string) {
  openTab(index)
}

function handleMenuSelect({ key }: { key: string }) {
  selectMenu(key)
  mobileSidebarOpen.value = false
}

function toggleSidebar() {
  if (isMobile.value) {
    mobileSidebarOpen.value = true
    return
  }
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function handleSidebarBreakpoint(broken: boolean) {
  isMobile.value = broken
  if (!broken) {
    mobileSidebarOpen.value = false
  }
}

function switchTab(name: string | number) {
  active.value = String(name)
  saveTabs()
}

async function closeTab(name: string | number) {
  const target = String(name)
  if (apiEditors[target]) {
    await requestCloseApiEditor(apiEditors[target])
    return
  }
  if (planEditors[target]) {
    await requestClosePlanEditor(planEditors[target])
    return
  }
  removeTab(target)
}

function handleTabEdit(targetKey: string | number, action: 'add' | 'remove') {
  if (action === 'remove') {
    void closeTab(targetKey)
  }
}

function removeTab(target: string) {
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
    message.warning('两次输入的新密码不一致')
    return false
  }
  return true
}

async function changePassword() {
  if (!changePasswordForm.old_password) {
    message.warning('请输入原密码')
    return
  }
  if (!changePasswordForm.new_password) {
    message.warning('请输入新密码')
    return
  }
  if (changePasswordForm.new_password.length < 6) {
    message.warning('新密码至少6位')
    return
  }
  if (!changePasswordForm.confirm_password) {
    message.warning('请再次输入新密码')
    return
  }
  if (passwordsMismatch()) {
    message.warning('两次输入的新密码不一致')
    return
  }
  if (changePasswordForm.old_password === changePasswordForm.new_password) {
    message.warning('新密码不能与原密码一致')
    return
  }
  try {
    await api.post('/auth/change-password', {
      old_password: changePasswordForm.old_password,
      new_password: changePasswordForm.new_password
    })
    changePasswordDialogVisible.value = false
    resetChangePasswordForm()
    message.success('密码修改成功')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '原密码错误')
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
    message.warning('请输入用户名')
    return
  }
  if (!realName) {
    message.warning('请输入姓名')
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
  message.success('用户已创建')
  await loadUsers()
}

async function updateUser() {
  const username = editUserForm.username.trim()
  const realName = editUserForm.real_name.trim()
  if (!username) {
    message.warning('请输入用户名')
    return
  }
  if (!realName) {
    message.warning('请输入姓名')
    return
  }
  await api.put(`/users/${editUserForm.id}`, { username, real_name: realName })
  editUserDialogVisible.value = false
  resetEditUserForm()
  message.success('用户已更新')
  await loadUsers()
}

async function toggleUserStatus(user: any) {
  const nextStatus = user.status === 'active' ? 'disabled' : 'active'
  await api.patch(`/users/${user.id}/status`, { status: nextStatus })
  message.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
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
    message.warning('请输入项目名称')
    return
  }
  if (!description) {
    message.warning('请输入描述')
    return
  }
  if (projects.value.some(project => project.name === name)) {
    message.warning('项目名称已存在')
    return
  }
  try {
    await api.post('/projects', { name, description })
    createProjectDialogVisible.value = false
    resetProjectForm()
    message.success('项目已创建')
    await refreshProjectsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '项目创建失败')
  }
}

async function updateProject() {
  const name = editProjectForm.name.trim()
  if (!name) {
    message.warning('请输入项目名称')
    return
  }
  await api.put(`/projects/${editProjectForm.id}`, { name, description: editProjectForm.description })
  editProjectDialogVisible.value = false
  resetEditProjectForm()
  message.success('项目已更新')
  await refreshProjectsAfterChange()
}

async function deleteProject(project: any) {
  try {
    await confirmAction('确认删除该项目吗？', '删除项目', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/projects/${project.id}`)
  message.success('项目已删除')
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
    message.warning('请选择协议')
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
    message.warning('请选择项目')
    return
  }
  if (!name) {
    message.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    message.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    message.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name)) {
    message.warning('环境名称已存在')
    return
  }
  try {
    await api.post('/environments', { project_id: projectId, name, protocol, base_url: baseUrl, port, headers: {}, variables: {} })
    createEnvironmentDialogVisible.value = false
    resetEnvironmentForm()
    message.success('环境已创建')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '环境创建失败')
  }
}

async function updateEnvironment() {
  const projectId = editEnvironmentForm.project_id
  const name = editEnvironmentForm.name.trim()
  const protocol = editEnvironmentForm.protocol
  const baseUrl = editEnvironmentForm.base_url.trim()
  const port = environmentPort(protocol, editEnvironmentForm.port)
  if (!projectId) {
    message.warning('请选择项目')
    return
  }
  if (!name) {
    message.warning('请输入环境名称')
    return
  }
  if (!protocol) {
    message.warning('请选择协议')
    return
  }
  if (!baseUrl) {
    message.warning('请输入 Base URL')
    return
  }
  if (environmentNameExists(projectId, name, editEnvironmentForm.id)) {
    message.warning('环境名称已存在')
    return
  }
  try {
    await api.put(`/environments/${editEnvironmentForm.id}`, { project_id: projectId, name, protocol, base_url: baseUrl, port })
    editEnvironmentDialogVisible.value = false
    resetEditEnvironmentForm()
    message.success('环境已更新')
    await refreshEnvironmentsAfterChange()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '环境更新失败')
  }
}

async function deleteEnvironment(environment: any) {
  try {
    await confirmAction('确认删除该环境吗？', '删除环境', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/environments/${environment.id}`)
  message.success('环境已删除')
  await refreshEnvironmentsAfterDelete()
}

async function refreshApisAfterChange() {
  await Promise.all([
    api.get('/apis').then(r => apis.value = r.data),
    loadApis()
  ])
}

async function refreshApisAfterDelete() {
  await refreshApisAfterChange()
  if (apiList.value.length === 0 && apiPagination.page > 1) {
    apiPagination.page -= 1
    await loadApis()
  }
}

function apiNameExists(projectId: number, name: string, apiId?: number) {
  return apis.value.some(item =>
    item.project_id === projectId &&
    item.name === name &&
    item.id !== apiId
  )
}

let apiRowId = 1
let caseAssertionRowId = 1
let caseExtractorRowId = 1
const contentTypes: Record<ApiEditor['bodyFormat'], string> = {
  json: 'application/json',
  xml: 'application/xml',
  'x-www-form-data': 'application/x-www-form-urlencoded'
}

function nextApiRow(key = '', value = ''): KeyValueRow {
  return { id: apiRowId++, key, value }
}

function nextCaseAssertionRow(type = 'status_code', path = '', operator = '==', expected = ''): CaseAssertionRow {
  return { id: caseAssertionRowId++, type, path, operator, expected }
}

function nextCaseExtractorRow(name = '', path = ''): CaseExtractorRow {
  return { id: caseExtractorRowId++, name, path }
}

function defaultHeaderRows() {
  return [
    nextApiRow('Connection', 'keep-alive'),
    nextApiRow('Accept-Encoding', 'gzip, deflate, br'),
    nextApiRow('Content-Type', contentTypes.json)
  ]
}

function objectToRows(value: any, fallback: KeyValueRow[] = []) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return fallback
  }
  return Object.entries(value).map(([key, rowValue]) => nextApiRow(key, String(rowValue ?? '')))
}

function mergeDefaultHeaders(rows: KeyValueRow[]) {
  const merged = [...rows]
  defaultHeaderRows().forEach(defaultRow => {
    if (!merged.some(row => row.key.trim().toLowerCase() === defaultRow.key.toLowerCase())) {
      merged.push(defaultRow)
    }
  })
  return merged
}

function bodyFormatFromApi(row: any): ApiEditor['bodyFormat'] {
  const format = row?.body?.format
  if (format === 'xml' || format === 'x-www-form-data') {
    return format
  }
  return 'json'
}

function createEmptyApiEditor(): ApiEditor {
  const editor: ApiEditor = {
    tabName: 'api-create',
    label: '新增接口',
    mode: 'create',
    project_id: undefined,
    name: '',
    description: '',
    method: 'GET',
    path: '',
    bodyFormat: 'json',
    activePanel: '',
    queryRows: [],
    headerRows: defaultHeaderRows(),
    preScript: '',
    encryption: {
      enabled: false,
      mode: 'none',
      encryptRequest: false,
      decryptResponse: false,
    },
    auth: defaultApiAuth(),
    dirty: false
  }
  return editor
}

function defaultApiAuth(): ApiAuth {
  return {
    type: 'none',
    addTo: 'headers',
    headerName: 'Authorization',
    headerPrefix: 'Bearer',
    token: '',
    username: '',
    password: '',
    apiKeyName: '',
    apiKeyValue: '',
    tokenUrl: '',
    clientId: '',
    clientSecret: '',
    scope: '',
    audience: '',
    clientAuthentication: 'body',
    currentToken: '',
    loading: false,
  }
}

function encryptionFromApi(row: any): ApiEncryption {
  const encryption = row.encryption || {}
  const enabled = encryption.mode === 'rsa_aes_sm3'
  return {
    enabled,
    mode: enabled ? 'rsa_aes_sm3' : 'none',
    encryptRequest: Boolean(encryption.encrypt_request),
    decryptResponse: Boolean(encryption.decrypt_response),
  }
}

function authFromApi(row: any): ApiAuth {
  const auth = row.auth || {}
  return {
    ...defaultApiAuth(),
    type: auth.type || 'none',
    addTo: auth.add_to || 'headers',
    headerName: auth.header_name || 'Authorization',
    headerPrefix: auth.header_prefix || 'Bearer',
    token: auth.token || '',
    username: auth.username || '',
    password: auth.password || '',
    apiKeyName: auth.api_key_name || '',
    apiKeyValue: auth.api_key_value || '',
    tokenUrl: auth.token_url || '',
    clientId: auth.client_id || '',
    clientSecret: auth.client_secret || '',
    scope: auth.scope || '',
    audience: auth.audience || '',
    clientAuthentication: auth.client_authentication || 'body',
  }
}

function createEditApiEditor(row: any): ApiEditor {
  const savedHeaderRows = objectToRows(row.headers)
  const editor: ApiEditor = {
    tabName: `api-edit-${row.id}`,
    label: '编辑接口',
    mode: 'edit',
    apiId: row.id,
    project_id: row.project_id,
    name: row.name || '',
    description: row.description || '',
    method: row.method || 'GET',
    path: row.path || '',
    bodyFormat: bodyFormatFromApi(row),
    activePanel: '',
    queryRows: objectToRows(row.query),
    headerRows: mergeDefaultHeaders(savedHeaderRows),
    preScript: row.pre_script || '',
    encryption: encryptionFromApi(row),
    auth: authFromApi(row),
    dirty: false
  }
  syncApiEditorContentType(editor, false)
  return editor
}

function openCreateApiDialog() {
  if (!apiEditors['api-create']) {
    apiEditors['api-create'] = createEmptyApiEditor()
  }
  openRuntimeTab({ name: 'api-create', label: '新增接口', closable: true })
}

function openEditApiDialog(row: any) {
  const tabName = `api-edit-${row.id}`
  if (!apiEditors[tabName]) {
    apiEditors[tabName] = createEditApiEditor(row)
  }
  openRuntimeTab({ name: tabName, label: '编辑接口', closable: true })
}

function markApiEditorDirty(editor: ApiEditor) {
  editor.dirty = true
}

function changeApiEditorProject(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function apiEditorEnvironment(editor: ApiEditor) {
  return environments.value.find(item => item.project_id === editor.project_id)
}

function environmentBaseUrl(environment: any) {
  if (!environment) return ''
  const baseUrl = String(environment.base_url || '').trim().replace(/\/+$/, '')
  const protocol = environment.protocol || 'http'
  const defaultPort = protocol === 'http' ? 80 : 443
  const port = environment.port && Number(environment.port) !== defaultPort ? `:${environment.port}` : ''
  return /^https?:\/\//i.test(baseUrl) ? baseUrl : `${protocol}://${baseUrl.replace(/^\/+/, '')}${port}`
}

function joinUrl(root: string, path: string) {
  if (!root) return ''
  if (/^https?:\/\//i.test(String(path || '').trim())) {
    return String(path || '').trim()
  }
  return `${root.replace(/\/+$/, '')}/${String(path || '').replace(/^\/+/, '')}`
}

function urlOrigin(url: string) {
  try {
    return new URL(url).origin
  } catch {
    return ''
  }
}

function apiEditorAuthRoot(editor: ApiEditor) {
  const path = editor.path.trim()
  if (/^https?:\/\//i.test(path)) {
    return urlOrigin(path)
  }
  return environmentBaseUrl(apiEditorEnvironment(editor))
}

function apiEditorScopeUrl(editor: ApiEditor) {
  const path = editor.path.trim()
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) {
    return path
  }
  return joinUrl(environmentBaseUrl(apiEditorEnvironment(editor)), path)
}

function generateApiAuthUrls(editor: ApiEditor, force = false, dirty = true) {
  if (editor.auth.type !== 'oauth2_client_credentials') return
  const root = apiEditorAuthRoot(editor)
  const scope = apiEditorScopeUrl(editor)
  let changed = false
  if ((force || !editor.auth.tokenUrl) && root) {
    editor.auth.tokenUrl = joinUrl(root, '/OAuth/Oauth/Token')
    changed = true
  }
  if ((force || !editor.auth.scope) && scope) {
    editor.auth.scope = scope
    changed = true
  }
  if (dirty && changed) {
    markApiEditorDirty(editor)
  }
}

function applyApiAuthDefaults(editor: ApiEditor) {
  if (editor.auth.type !== 'oauth2_client_credentials') return
  generateApiAuthUrls(editor, false, false)
}

function changeApiAuthType(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function changeApiEditorPath(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  markApiEditorDirty(editor)
}

function syncApiEditorContentType(editor: ApiEditor, dirty = true) {
  const row = editor.headerRows.find(item => item.key.trim().toLowerCase() === 'content-type')
  if (row) {
    row.value = contentTypes[editor.bodyFormat]
  } else {
    editor.headerRows.push(nextApiRow('Content-Type', contentTypes[editor.bodyFormat]))
  }
  if (dirty) {
    markApiEditorDirty(editor)
  }
}

function changeApiEditorBodyFormat(editor: ApiEditor) {
  syncApiEditorContentType(editor)
}

function addApiEditorRow(rows: KeyValueRow[], key = '') {
  rows.push(nextApiRow(key, ''))
  if (activeApiEditor.value) {
    markApiEditorDirty(activeApiEditor.value)
  }
}

function removeApiEditorRow(rows: KeyValueRow[], index: number, editor: ApiEditor) {
  rows.splice(index, 1)
  markApiEditorDirty(editor)
}

function rowsToObject(rows: KeyValueRow[]) {
  return rows.reduce<Record<string, string>>((result, row) => {
    const key = row.key.trim()
    if (key) {
      result[key] = row.value
    }
    return result
  }, {})
}

function upsertApiEditorHeader(editor: ApiEditor, key: string, value: string) {
  const headerKey = key.trim()
  if (!headerKey) return
  const row = editor.headerRows.find(item => item.key.trim().toLowerCase() === headerKey.toLowerCase())
  if (row) {
    row.value = value
  } else {
    editor.headerRows.push(nextApiRow(headerKey, value))
  }
  markApiEditorDirty(editor)
}

function upsertApiEditorQuery(editor: ApiEditor, key: string, value: string) {
  const queryKey = key.trim()
  if (!queryKey) return
  const row = editor.queryRows.find(item => item.key.trim() === queryKey)
  if (row) {
    row.value = value
  } else {
    editor.queryRows.push(nextApiRow(queryKey, value))
  }
  markApiEditorDirty(editor)
}

function apiPayload(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  const headers = rowsToObject(editor.headerRows)
  return {
    project_id: editor.project_id,
    name: editor.name.trim(),
    description: editor.description.trim(),
    method: editor.method,
    path: editor.path.trim(),
    headers,
    query: rowsToObject(editor.queryRows),
    body: { format: editor.bodyFormat },
    pre_script: editor.preScript,
    encryption: {
      mode: editor.encryption.enabled ? editor.encryption.mode : 'none',
      encrypt_request: editor.encryption.enabled && editor.encryption.encryptRequest,
      decrypt_response: editor.encryption.enabled && editor.encryption.decryptResponse,
      client_header: 'appKey'
    },
    auth: {
      type: editor.auth.type,
      add_to: editor.auth.addTo,
      header_name: editor.auth.headerName || 'Authorization',
      header_prefix: editor.auth.headerPrefix || 'Bearer',
      token: editor.auth.token,
      username: editor.auth.username,
      password: editor.auth.password,
      api_key_name: editor.auth.apiKeyName,
      api_key_value: editor.auth.apiKeyValue,
      token_url: editor.auth.tokenUrl,
      client_id: editor.auth.clientId,
      client_secret: editor.auth.clientSecret,
      scope: editor.auth.scope,
      audience: editor.auth.audience,
      client_authentication: editor.auth.clientAuthentication
    }
  }
}

async function getApiEditorAccessToken(editor: ApiEditor) {
  applyApiAuthDefaults(editor)
  const environment = apiEditorEnvironment(editor)
  if (!environment?.id) {
    message.warning('请先选择存在环境配置的项目')
    return
  }
  if (!editor.auth.tokenUrl) {
    message.warning('请输入 Access Token URL')
    return
  }
  if (!editor.auth.clientId) {
    message.warning('请输入 Client ID')
    return
  }
  editor.auth.loading = true
  try {
    const { data } = await api.post('/apis/auth/token', {
      environment_id: environment.id,
      path: editor.path.trim() || '/',
      auth: apiPayload(editor).auth
    })
    editor.auth.currentToken = data.access_token || ''
    if (editor.auth.currentToken) {
      const headerName = editor.auth.headerName || 'Authorization'
      const headerPrefix = editor.auth.headerPrefix || 'Bearer'
      if (editor.auth.addTo === 'query') {
        upsertApiEditorQuery(editor, 'access_token', editor.auth.currentToken)
        editor.activePanel = 'query'
      } else {
        upsertApiEditorHeader(editor, headerName, `${headerPrefix} ${editor.auth.currentToken}`.trim())
        editor.activePanel = 'headers'
      }
    }
    message.success('Access Token 获取成功')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || 'Access Token 获取失败')
  } finally {
    editor.auth.loading = false
  }
}

function validateApiEditor(editor: ApiEditor) {
  const payload = apiPayload(editor)
  if (!payload.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!payload.name) {
    message.warning('请输入接口名称')
    return null
  }
  if (!payload.path) {
    message.warning('请输入接口路径')
    return null
  }
  if (apiNameExists(payload.project_id, payload.name, editor.apiId)) {
    message.warning('接口名称已存在')
    return null
  }
  return payload
}

async function saveApiEditor(editor: ApiEditor, closeAfterSave = false) {
  const payload = validateApiEditor(editor)
  if (!payload) {
    return false
  }
  try {
    if (editor.mode === 'edit') {
      await api.put(`/apis/${editor.apiId}`, payload)
      message.success('接口已更新')
    } else {
      const { data } = await api.post('/apis', payload)
      message.success('接口已创建')
      if (!closeAfterSave) {
        promoteCreatedApiEditor(editor, data.id)
      }
    }
    editor.dirty = false
    await refreshApisAfterChange()
    if (closeAfterSave) {
      closeApiEditorSilently(editor.tabName)
    }
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '接口保存失败')
    return false
  }
}

function promoteCreatedApiEditor(editor: ApiEditor, apiId: number) {
  const oldTabName = editor.tabName
  const newTabName = `api-edit-${apiId}`
  delete apiEditors[oldTabName]
  editor.tabName = newTabName
  editor.label = '编辑接口'
  editor.mode = 'edit'
  editor.apiId = apiId
  apiEditors[newTabName] = editor
  const tab = openedTabs.value.find(item => item.name === oldTabName)
  if (tab) {
    tab.name = newTabName
    tab.label = editor.label
  }
  active.value = newTabName
  saveTabs()
}

function closeApiEditorSilently(tabName: string) {
  delete apiEditors[tabName]
  removeTab(tabName)
}

async function requestCloseApiEditor(editor: ApiEditor) {
  if (!editor.dirty) {
    closeApiEditorSilently(editor.tabName)
    return
  }
  try {
    await confirmAction('当前接口内容尚未保存，是否保存后关闭？', '关闭接口', {
      confirmButtonText: '保存并关闭',
      cancelButtonText: '不保存关闭',
      distinguishCancelAndClose: true,
      type: 'warning'
    })
    await saveApiEditor(editor, true)
  } catch (action) {
    if (action === 'cancel') {
      closeApiEditorSilently(editor.tabName)
    }
  }
}

async function closeApiEditorFromPage(editor: ApiEditor) {
  await requestCloseApiEditor(editor)
}

async function deleteApi(row: any) {
  try {
    await confirmAction('确认删除该接口吗？', '删除接口', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/apis/${row.id}`)
    message.success('接口已删除')
    await refreshApisAfterDelete()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '接口删除失败')
  }
}

function resetCaseForm() {
  caseForm.id = undefined
  caseForm.project_id = undefined
  caseForm.api_id = undefined
  caseForm.name = ''
  caseForm.description = ''
  caseForm.bodyText = '{}'
  caseForm.assertionRows = []
  caseForm.extractorRows = []
}

function openCreateCasePage() {
  resetCaseForm()
  openRuntimeTab({ name: 'case-create', label: '新增用例', closable: true })
}

function openEditCasePage(row: any) {
  caseForm.id = row.id
  caseForm.project_id = row.project_id
  caseForm.api_id = row.api_id
  caseForm.name = row.name || ''
  caseForm.description = row.tags || ''
  caseForm.bodyText = JSON.stringify(row.request_body ?? {}, null, 2)
  caseForm.assertionRows = caseAssertionsToRows(row.assertions)
  caseForm.extractorRows = caseExtractorsToRows(row.extractors)
  openRuntimeTab({ name: `case-edit-${row.id}`, label: '编辑用例', closable: true })
}

function closeCaseEditorPage() {
  const target = active.value
  resetCaseForm()
  removeTab(target)
}

function changeCaseFormProject() {
  caseForm.api_id = undefined
}

function caseAssertionsToRows(assertions: any[]): CaseAssertionRow[] {
  if (!Array.isArray(assertions)) {
    return []
  }
  return assertions.map(item => nextCaseAssertionRow(
    item?.type || 'status_code',
    item?.path || '',
    item?.operator || '==',
    String(item?.expected ?? '')
  ))
}

function caseExtractorsToRows(extractors: any[]): CaseExtractorRow[] {
  if (!Array.isArray(extractors)) {
    return []
  }
  return extractors.map(item => nextCaseExtractorRow(item?.name || '', item?.path || ''))
}

function caseAssertionRowsToPayload() {
  return caseForm.assertionRows
    .filter(row => row.type)
    .map(row => ({
      type: row.type,
      path: row.path.trim(),
      operator: row.operator.trim() || '==',
      expected: parseAssertionExpected(row.expected)
    }))
}

function caseExtractorRowsToPayload() {
  return caseForm.extractorRows
    .map(row => ({ name: row.name.trim(), path: row.path.trim() }))
    .filter(row => row.name && row.path)
}

function parseAssertionExpected(value: string) {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }
  try {
    return JSON.parse(trimmed)
  } catch {
    return trimmed
  }
}

function addCaseAssertionRow() {
  caseForm.assertionRows.push(nextCaseAssertionRow())
}

function removeCaseAssertionRow(index: number) {
  caseForm.assertionRows.splice(index, 1)
}

function addCaseExtractorRow() {
  caseForm.extractorRows.push(nextCaseExtractorRow())
}

function removeCaseExtractorRow(index: number) {
  caseForm.extractorRows.splice(index, 1)
}

function validateCaseForm() {
  if (!caseForm.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!caseForm.api_id) {
    message.warning('请选择接口')
    return null
  }
  const name = caseForm.name.trim()
  if (!name) {
    message.warning('请输入用例名称')
    return null
  }
  const requestBody = parseJson(caseForm.bodyText, undefined)
  if (requestBody === undefined) {
    message.warning('Body 必须是合法 JSON')
    return null
  }
  return {
    project_id: caseForm.project_id,
    api_id: caseForm.api_id,
    name,
    request_headers: {},
    request_query: {},
    request_body: requestBody,
    assertions: caseAssertionRowsToPayload(),
    extractors: caseExtractorRowsToPayload(),
    tags: caseForm.description.trim(),
  }
}

function openCaseBodyDialog(row: any) {
  caseBodyPreview.value = JSON.stringify(row.request_body ?? {}, null, 2)
  caseBodyDialogVisible.value = true
}

async function saveCase() {
  const payload = validateCaseForm()
  if (!payload) {
    return
  }
  try {
    if (caseForm.id) {
      await api.put(`/cases/${caseForm.id}`, payload)
      message.success('用例已更新')
    } else {
      await api.post('/cases', payload)
      message.success('用例已创建')
    }
    caseSearch.project_id = payload.project_id
    caseSearch.api_id = payload.api_id
    resetCaseForm()
    await loadCases()
    await refreshAllCases()
    closeCaseEditorPage()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '用例保存失败')
  }
}

async function deleteCase(row: any) {
  try {
    await confirmAction('确认删除该用例吗？', '删除用例', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/cases/${row.id}`)
    message.success('用例已删除')
    await loadCases()
    if (caseList.value.length === 0 && casePagination.page > 1) {
      casePagination.page -= 1
      await loadCases()
    }
    await refreshAllCases()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '用例删除失败')
  }
}

function createEmptyPlanEditor(): PlanEditor {
  return {
    tabName: 'plan-create',
    label: '新增测试计划',
    mode: 'create',
    project_id: undefined,
    environment_id: undefined,
    api_id: undefined,
    name: '',
    candidateCases: [],
    selectedCases: [],
    queue: [],
    dirty: false
  }
}

function createEditPlanEditor(row: any): PlanEditor {
  return {
    tabName: `plan-edit-${row.id}`,
    label: '编辑测试计划',
    mode: 'edit',
    planId: row.id,
    project_id: row.project_id,
    environment_id: row.environment_id,
    api_id: row.api_id,
    name: row.name || '',
    candidateCases: [],
    selectedCases: [],
    queue: [...(row.cases || [])],
    dirty: false
  }
}

function openCreatePlanPage() {
  if (!planEditors['plan-create']) {
    planEditors['plan-create'] = createEmptyPlanEditor()
  }
  openRuntimeTab({ name: 'plan-create', label: '新增测试计划', closable: true })
}

function openEditPlanPage(row: any) {
  const tabName = `plan-edit-${row.id}`
  if (!planEditors[tabName]) {
    planEditors[tabName] = createEditPlanEditor(row)
  }
  openRuntimeTab({ name: tabName, label: '编辑测试计划', closable: true })
}

function markPlanEditorDirty(editor: PlanEditor) {
  editor.dirty = true
}

function planEditorEnvironments(editor: PlanEditor) {
  return environments.value.filter(item => editor.project_id && item.project_id === editor.project_id)
}

function planEditorApis(editor: PlanEditor) {
  return apis.value.filter(item => editor.project_id && item.project_id === editor.project_id)
}

function changePlanEditorProject(editor: PlanEditor) {
  editor.environment_id = undefined
  editor.api_id = undefined
  editor.candidateCases = []
  editor.selectedCases = []
  markPlanEditorDirty(editor)
}

function changePlanEditorApi(editor: PlanEditor) {
  editor.candidateCases = []
  editor.selectedCases = []
  markPlanEditorDirty(editor)
}

function planNameExists(projectId: number, name: string, planId?: number) {
  return planList.value.some(item =>
    item.project_id === projectId &&
    item.name === name &&
    item.id !== planId
  )
}

function validatePlanEditor(editor: PlanEditor) {
  if (!editor.project_id) {
    message.warning('请选择项目')
    return null
  }
  if (!editor.environment_id) {
    message.warning('请选择环境')
    return null
  }
  if (!editor.api_id) {
    message.warning('请选择接口')
    return null
  }
  const name = editor.name.trim()
  if (!name) {
    message.warning('请输入测试计划名称')
    return null
  }
  if (planNameExists(editor.project_id, name, editor.planId)) {
    message.warning('测试计划名称已存在')
    return null
  }
  if (editor.queue.length === 0) {
    message.warning('请至少添加一条测试用例')
    return null
  }
  return {
    project_id: editor.project_id,
    environment_id: editor.environment_id,
    api_id: editor.api_id,
    name,
    items: editor.queue.map(item => item.id)
  }
}

async function loadPlanCandidateCases(editor: PlanEditor) {
  if (!editor.project_id || !editor.environment_id || !editor.api_id) {
    message.warning('请先选择项目、环境和接口')
    return
  }
  const { data } = await api.get('/cases', {
    params: {
      project_id: editor.project_id,
      api_id: editor.api_id
    }
  })
  editor.candidateCases = data
  editor.selectedCases = []
}

function changePlanCandidateSelection(editor: PlanEditor, rows: any[]) {
  editor.selectedCases = rows
}

function addSelectedPlanCases(editor: PlanEditor) {
  const exists = new Set(editor.queue.map(item => item.id))
  editor.selectedCases.forEach(item => {
    if (!exists.has(item.id)) {
      editor.queue.push(item)
      exists.add(item.id)
    }
  })
  markPlanEditorDirty(editor)
}

function removePlanQueueCase(editor: PlanEditor, index: number) {
  editor.queue.splice(index, 1)
  markPlanEditorDirty(editor)
}

function startPlanQueueDrag(editor: PlanEditor, index: number) {
  editor.dragIndex = index
}

function dropPlanQueueRow(editor: PlanEditor, index: number) {
  const from = editor.dragIndex
  editor.dragIndex = undefined
  if (from === undefined || from === index) {
    return
  }
  const [row] = editor.queue.splice(from, 1)
  editor.queue.splice(index, 0, row)
  markPlanEditorDirty(editor)
}

async function savePlanEditor(editor: PlanEditor, closeAfterSave = false) {
  const payload = validatePlanEditor(editor)
  if (!payload) {
    return false
  }
  try {
    if (editor.mode === 'edit') {
      await api.put(`/plans/${editor.planId}`, payload)
      message.success('测试计划已更新')
    } else {
      const { data } = await api.post('/plans', payload)
      message.success('测试计划已创建')
      if (!closeAfterSave) {
        promoteCreatedPlanEditor(editor, data.id)
      }
    }
    editor.dirty = false
    planSearch.project_id = payload.project_id
    planSearch.api_id = payload.api_id
    await refreshPlansAfterChange()
    if (closeAfterSave) {
      closePlanEditorSilently(editor.tabName)
    }
    return true
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '测试计划保存失败')
    return false
  }
}

function promoteCreatedPlanEditor(editor: PlanEditor, planId: number) {
  const oldTabName = editor.tabName
  const newTabName = `plan-edit-${planId}`
  delete planEditors[oldTabName]
  editor.tabName = newTabName
  editor.label = '编辑测试计划'
  editor.mode = 'edit'
  editor.planId = planId
  planEditors[newTabName] = editor
  const tab = openedTabs.value.find(item => item.name === oldTabName)
  if (tab) {
    tab.name = newTabName
    tab.label = editor.label
  }
  active.value = newTabName
  saveTabs()
}

function closePlanEditorSilently(tabName: string) {
  delete planEditors[tabName]
  removeTab(tabName)
}

async function requestClosePlanEditor(editor: PlanEditor) {
  if (!editor.dirty) {
    closePlanEditorSilently(editor.tabName)
    return
  }
  try {
    await confirmAction('当前测试计划内容尚未保存，是否保存后关闭？', '关闭测试计划', {
      confirmButtonText: '保存并关闭',
      cancelButtonText: '不保存关闭',
      distinguishCancelAndClose: true,
      type: 'warning'
    })
    await savePlanEditor(editor, true)
  } catch (action) {
    if (action === 'cancel') {
      closePlanEditorSilently(editor.tabName)
    }
  }
}

async function closePlanEditorFromPage(editor: PlanEditor) {
  await requestClosePlanEditor(editor)
}

async function deletePlan(row: any) {
  try {
    await confirmAction('确认删除该测试计划吗？', '删除测试计划', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/plans/${row.id}`)
  message.success('测试计划已删除')
  await loadPlans()
}

function clearPlanExecutionPoller(planId: number) {
  const timer = planExecutionPollers.get(planId)
  if (timer) {
    window.clearInterval(timer)
    planExecutionPollers.delete(planId)
  }
}

function updatePlanExecutionState(planId: number, taskId: number, status: string, row?: any) {
  if (row) {
    row.last_execution_id = taskId
    row.last_status = status
  }
  const target = planList.value.find(item => item.id === planId)
  if (target) {
    target.last_execution_id = taskId
    target.last_status = status
  }
}

async function refreshExecutionViews() {
  await Promise.all([
    loadReports(),
    api.get('/executions').then(r => executions.value = r.data)
  ])
}

function pollPlanExecution(planId: number, taskId: number, row?: any) {
  clearPlanExecutionPoller(planId)
  let attempts = 0
  let polling = false
  const terminalStatuses = new Set(['passed', 'failed', 'error'])
  const poll = async () => {
    if (polling) return
    polling = true
    attempts += 1
    try {
      const { data } = await api.get(`/executions/${taskId}`)
      const status = data?.task?.status || ''
      if (status) {
        updatePlanExecutionState(planId, taskId, status, row)
      }
      if (terminalStatuses.has(status) || attempts >= 30) {
        clearPlanExecutionPoller(planId)
        await Promise.all([loadPlans(), refreshExecutionViews()])
      }
    } catch {
      if (attempts >= 30) {
        clearPlanExecutionPoller(planId)
      }
    } finally {
      polling = false
    }
  }
  const timer = window.setInterval(poll, 1000)
  planExecutionPollers.set(planId, timer)
  void poll()
}

async function executePlan(row: any) {
  clearPlanExecutionPoller(row.id)
  const { data } = await api.post(`/plans/${row.id}/execute`)
  const taskId = data.id
  const status = data.status || 'queued'
  updatePlanExecutionState(row.id, taskId, status, row)
  message.success('执行任务已提交')
  await refreshExecutionViews()
  pollPlanExecution(row.id, taskId, row)
}

function findCaseApi(row: any) {
  return apis.value.find(item => item.id === row.api_id)
}

function findCaseEnvironment(row: any, environmentId?: number) {
  const apiRow = findCaseApi(row)
  return environments.value.find(item => item.id === environmentId) ||
    environments.value.find(item => apiRow?.environment_id && item.id === apiRow.environment_id)
}

function buildFullRequestUrl(environment: any, apiRow: any, query: Record<string, any>) {
  if (!apiRow) {
    return ''
  }
  const baseUrl = String(environment?.base_url || '').trim().replace(/\/+$/, '')
  const protocol = environment?.protocol || 'http'
  const defaultPort = protocol === 'http' ? 80 : 443
  const port = environment?.port && Number(environment.port) !== defaultPort ? `:${environment.port}` : ''
  const root = /^https?:\/\//i.test(baseUrl) ? baseUrl : `${protocol}://${baseUrl.replace(/^\/+/, '')}${port}`
  const path = String(apiRow.path || '').replace(/^\/+/, '')
  const url = `${root}/${path}`
  const queryText = new URLSearchParams(
    Object.entries(query || {}).reduce<Record<string, string>>((result, [key, value]) => {
      if (key.trim()) {
        result[key] = String(value ?? '')
      }
      return result
    }, {})
  ).toString()
  return queryText ? `${url}?${queryText}` : url
}

async function openCaseDetailDialog(row: any, environmentId?: number, executionId?: number) {
  const apiRow = apis.value.find(item => item.id === row.api_id)
  const environment = findCaseEnvironment(row, environmentId)
  const requestQuery = { ...(apiRow?.query || {}), ...(row.request_query || {}) }
  const requestHeaders = { ...(environment?.headers || {}), ...(apiRow?.headers || {}), ...(row.request_headers || {}) }
  let responseSnapshot: any = {}
  let requestSnapshot: any = {}
  if (executionId && row.id) {
    try {
      const { data } = await api.get(`/executions/${executionId}`)
      const result = (data.results || []).find((item: any) => item.case_id === row.id)
      responseSnapshot = result?.response_snapshot || {}
      requestSnapshot = result?.request_snapshot || {}
    } catch {}
  }
  Object.keys(caseDetail).forEach(key => delete caseDetail[key])
  Object.assign(caseDetail, {
    method: row.method || apiRow?.method || '',
    url: buildFullRequestUrl(environment, apiRow || row, requestQuery),
    request_headers: requestHeaders,
    request_body: requestSnapshot.body ?? row.request_body ?? {},
    request_body_original: requestSnapshot.body_original,
    assertions: row.assertions || [],
    extractors: row.extractors || [],
    extracted_variables: responseSnapshot.extracted_variables || [],
    response_snapshot: responseSnapshot
  })
  caseDetailDialogVisible.value = true
}

function formatJson(value: any) {
  return JSON.stringify(value ?? {}, null, 2)
}

function formatMinute(value: string) {
  return value ? value.slice(0, 16) : ''
}

function executionStatusColor(status: string) {
  if (status === 'passed') return 'success'
  if (status === 'failed' || status === 'error') return 'error'
  if (status === 'running') return 'warning'
  if (status === 'queued') return 'processing'
  return 'default'
}

function executionStatusText(status: string) {
  const labels: Record<string, string> = {
    queued: '排队中',
    running: '执行中',
    passed: '已通过',
    failed: '失败',
    error: '异常'
  }
  return labels[status] || '未执行'
}

async function openExecutionDetail(row: any) {
  if (!row.last_execution_id) {
    message.warning('该测试计划暂无执行记录')
    return
  }
  const { data } = await api.get(`/executions/${row.last_execution_id}`)
  executionDetail.task = data.task
  executionDetail.results = data.results || []
  executionDetailDialogVisible.value = true
}

async function openReport(row: any) {
  const reportWindow = window.open('', '_blank')
  if (!reportWindow) {
    message.warning('浏览器已拦截报告窗口，请允许弹窗后重试')
    return
  }
  reportWindow.document.write('<p style="font-family: Arial, sans-serif; padding: 24px;">报告加载中...</p>')
  try {
    const { data } = await api.get(`/executions/${row.id}/report`, { responseType: 'text' })
    reportWindow.document.open()
    reportWindow.document.write(data || '<h1>报告尚未生成</h1>')
    reportWindow.document.close()
  } catch (error: any) {
    reportWindow.document.open()
    reportWindow.document.write('<h1>报告加载失败</h1><p>请确认报告存在且当前账号仍处于登录状态。</p>')
    reportWindow.document.close()
    message.error(error?.response?.data?.detail || '报告加载失败')
  }
}

async function deleteReport(row: any) {
  try {
    await confirmAction('确认删除该报告吗？删除后报告中心将不再展示。', '删除报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/executions/${row.id}`)
  message.success('报告已删除')
  await loadReports()
}

async function runCase() {
  await api.post('/executions', { ...execForm, target_type: 'case' })
  message.success('执行任务已提交')
  await loadAll()
}

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    me.value = data
    await loadAll()
  } catch {}
})

onUnmounted(() => {
  Array.from(planExecutionPollers.keys()).forEach(clearPlanExecutionPoller)
})
</script>
