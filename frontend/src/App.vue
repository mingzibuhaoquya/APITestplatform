<template>
  <div v-if="!me" class="login-page">
    <el-card class="login-card">
      <h1>接口自动化测试平台</h1>
      <el-form label-position="top" @submit.prevent="login">
        <el-form-item label="用户名"><el-input v-model="loginForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="loginForm.password" type="password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit" class="full">登录</el-button>
      </el-form>
    </el-card>
  </div>

  <el-container v-else class="shell">
    <el-aside width="220px">
      <div class="brand">接口测试平台</div>
      <el-menu :default-active="active" @select="selectMenu">
        <el-menu-item index="dashboard">数据概览</el-menu-item>
        <el-sub-menu index="project-env">
          <template #title>项目环境</template>
          <el-menu-item index="projects">项目管理</el-menu-item>
          <el-menu-item index="environments">环境管理</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="apis">接口管理</el-menu-item>
        <el-menu-item index="cases">用例管理</el-menu-item>
        <el-menu-item index="execute">测试计划</el-menu-item>
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
          <div class="toolbar"><h2>项目管理</h2><el-button type="primary" @click="openCreateProjectDialog">创建项目</el-button></div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="项目名称">
              <el-input v-model="projectSearch.name" placeholder="请输入项目名称" clearable @keyup.enter="searchProjects" />
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchProjects">搜索</el-button>
              <el-button @click="resetProjectSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="projectList">
            <el-table-column prop="name" label="项目" />
            <el-table-column prop="description" label="描述" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEditProjectDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteProject(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
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

        <section v-if="active === 'environments'">
          <div class="toolbar"><h2>环境管理</h2><el-button type="primary" @click="openCreateEnvironmentDialog">新增环境</el-button></div>
          <el-form class="search-form" label-position="top">
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
          <el-table :data="environmentList">
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
          </el-table>
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

        <section v-if="active === 'apis'">
          <div class="toolbar"><h2>接口管理</h2><el-button type="primary" @click="openCreateApiDialog">新增接口</el-button></div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="项目">
              <el-select v-model="apiSearch.project_id" placeholder="请选择项目" clearable>
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="名称">
              <el-input v-model="apiSearch.name" placeholder="请输入接口名称" clearable @keyup.enter="searchApis" />
            </el-form-item>
            <el-form-item label="URL名称">
              <el-input v-model="apiSearch.url" placeholder="请输入接口路径" clearable @keyup.enter="searchApis" />
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchApis">搜索</el-button>
              <el-button @click="resetApiSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="apiList">
            <el-table-column prop="project_name" label="项目" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="description" label="接口描述" />
            <el-table-column prop="method" label="方法" width="100" />
            <el-table-column prop="path" label="路径" />
            <el-table-column prop="create_date" label="创建时间" width="170" />
            <el-table-column prop="update_date" label="更新时间" width="170" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openEditApiDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteApi(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="apiPagination.page"
              :page-size="apiPagination.pageSize"
              :total="apiPagination.total"
              @current-change="changeApiPage"
            />
          </div>

        </section>

        <section v-if="activeApiEditor" class="api-editor-page">
          <div class="toolbar">
            <h2>{{ activeApiEditor.label }}</h2>
            <div class="toolbar-actions">
              <el-button @click="closeApiEditorFromPage(activeApiEditor)">关闭</el-button>
              <el-button type="primary" @click="saveApiEditor(activeApiEditor)">保存</el-button>
            </div>
          </div>

          <div class="editor-section">
            <h3>基础信息</h3>
            <el-form label-position="top" class="form-grid">
              <el-form-item label="项目">
                <el-select
                  v-model="activeApiEditor.project_id"
                  placeholder="请选择项目"
                  @change="changeApiEditorProject(activeApiEditor)"
                >
                  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="名称">
                <el-input v-model="activeApiEditor.name" placeholder="请输入接口名称" @input="markApiEditorDirty(activeApiEditor)" />
              </el-form-item>
              <el-form-item label="接口描述" class="wide">
                <el-input v-model="activeApiEditor.description" type="textarea" :rows="3" placeholder="请输入接口描述" @input="markApiEditorDirty(activeApiEditor)" />
              </el-form-item>
            </el-form>
          </div>

          <div class="editor-section">
            <h3>接口信息</h3>
            <div class="request-line">
              <el-select v-model="activeApiEditor.method" placeholder="方法" class="method-select" @change="markApiEditorDirty(activeApiEditor)">
                <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
              </el-select>
              <el-input v-model="activeApiEditor.path" placeholder="请输入接口路径 URL，例如 /users" @input="markApiEditorDirty(activeApiEditor)" />
            </div>

            <el-tabs v-model="activeApiEditor.activePanel" class="api-info-tabs">
              <el-tab-pane label="URL参数" name="query">
                <div class="kv-title">
                  <h4>URL参数</h4>
                  <el-button size="small" @click="addApiEditorRow(activeApiEditor.queryRows)">添加</el-button>
                </div>
                <el-table :data="activeApiEditor.queryRows">
                  <el-table-column label="Key">
                    <template #default="{ row }"><el-input v-model="row.key" placeholder="key" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </el-table-column>
                  <el-table-column label="Value">
                    <template #default="{ row }"><el-input v-model="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </el-table-column>
                  <el-table-column label="操作" width="90">
                    <template #default="{ $index }"><el-button size="small" type="danger" @click="removeApiEditorRow(activeApiEditor.queryRows, $index, activeApiEditor)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="请求头Header" name="headers">
                <div class="kv-title">
                  <h4>请求头Header</h4>
                  <el-button size="small" @click="addApiEditorRow(activeApiEditor.headerRows)">添加</el-button>
                </div>
                <el-table :data="activeApiEditor.headerRows">
                  <el-table-column label="Key">
                    <template #default="{ row }"><el-input v-model="row.key" placeholder="Authorization / Content-Type" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </el-table-column>
                  <el-table-column label="Value">
                    <template #default="{ row }"><el-input v-model="row.value" placeholder="value" @input="markApiEditorDirty(activeApiEditor)" /></template>
                  </el-table-column>
                  <el-table-column label="操作" width="90">
                    <template #default="{ $index }"><el-button size="small" type="danger" @click="removeApiEditorRow(activeApiEditor.headerRows, $index, activeApiEditor)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <el-tab-pane label="请求Body" name="body">
                <div class="body-format-row">
                  <span>Body格式</span>
                  <el-radio-group v-model="activeApiEditor.bodyFormat" @change="changeApiEditorBodyFormat(activeApiEditor)">
                    <el-radio-button label="json">json</el-radio-button>
                    <el-radio-button label="xml">xml</el-radio-button>
                    <el-radio-button label="x-www-form-data">x-www-form-data</el-radio-button>
                  </el-radio-group>
                </div>
              </el-tab-pane>
              <el-tab-pane label="Pre-script" name="pre-script">
                <el-input
                  v-model="activeApiEditor.preScript"
                  type="textarea"
                  :rows="14"
                  class="pre-script-input"
                  placeholder="pm.environment.set('timestamp', Date.now());&#10;pm.environment.set('sign', CryptoJS.MD5(pm.environment.get('timestamp')).toString());"
                  @input="markApiEditorDirty(activeApiEditor)"
                />
                <p class="pre-script-hint">
                  支持 pm.environment.get/set、Date、Math、JSON、CryptoJS.MD5/SHA256 和 console.log/info/warn；不支持 require、网络请求、文件或数据库访问。
                </p>
              </el-tab-pane>
              <el-tab-pane label="加密配置" name="encryption">
                <el-form label-position="top">
                  <el-form-item label="启用接口加密">
                    <el-switch v-model="activeApiEditor.encryption.enabled" @change="markApiEditorDirty(activeApiEditor)" />
                  </el-form-item>
                  <template v-if="activeApiEditor.encryption.enabled">
                    <el-form-item label="加密方式">
                      <el-select v-model="activeApiEditor.encryption.mode" @change="markApiEditorDirty(activeApiEditor)">
                        <el-option label="RSA-AES-SM3" value="rsa_aes_sm3" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="处理方式">
                      <el-checkbox v-model="activeApiEditor.encryption.encryptRequest" @change="markApiEditorDirty(activeApiEditor)">请求 Body 加密</el-checkbox>
                      <el-checkbox v-model="activeApiEditor.encryption.decryptResponse" @change="markApiEditorDirty(activeApiEditor)">响应 Body 解密</el-checkbox>
                    </el-form-item>
                    <p class="pre-script-hint">平台使用服务器预置的固定 RSA 密钥，无需上传 PEM 文件。</p>
                  </template>
                </el-form>
              </el-tab-pane>
            </el-tabs>
          </div>
        </section>

        <section v-if="active === 'cases'">
          <div class="toolbar"><h2>用例管理</h2><el-button type="primary" @click="openCreateCasePage">新增用例</el-button></div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="项目">
              <el-select v-model="caseSearch.project_id" placeholder="请选择项目" clearable @change="changeCaseSearchProject">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="接口">
              <el-select v-model="caseSearch.api_id" placeholder="请先选择项目" clearable :disabled="!caseSearch.project_id">
                <el-option v-for="a in caseSearchApis" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchCases">搜索</el-button>
              <el-button @click="resetCaseSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="caseList">
            <el-table-column label="编号" width="80">
              <template #default="{ $index }">{{ caseSerialNumber($index) }}</template>
            </el-table-column>
            <el-table-column prop="project_name" label="项目" />
            <el-table-column prop="api_name" label="接口" />
            <el-table-column prop="name" label="用例名称" />
            <el-table-column prop="priority" label="优先级" width="100" />
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openCaseDetailDialog(row)">查看</el-button>
                <el-button size="small" @click="openEditCasePage(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteCase(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="casePagination.page"
              :page-size="casePagination.pageSize"
              :total="casePagination.total"
              @current-change="changeCasePage"
            />
          </div>
        </section>

        <section v-if="active === 'case-create' || active.startsWith('case-edit-')">
          <div class="toolbar">
            <h2>{{ caseForm.id ? '编辑用例' : '新增用例' }}</h2>
            <div class="toolbar-actions">
              <el-button @click="closeCaseEditorPage">关闭</el-button>
              <el-button type="primary" @click="saveCase">保存</el-button>
            </div>
          </div>
          <el-form label-position="top" class="form-grid">
            <el-form-item label="项目">
              <el-select v-model="caseForm.project_id" placeholder="请选择项目" @change="changeCaseFormProject">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="接口">
              <el-select v-model="caseForm.api_id" placeholder="请先选择项目" :disabled="!caseForm.project_id">
                <el-option v-for="a in caseFormApis" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="用例名称">
              <el-input v-model="caseForm.name" placeholder="请输入用例名称" />
            </el-form-item>
            <el-form-item label="优先级">
              <el-select v-model="caseForm.priority">
                <el-option label="P0" value="P0" />
                <el-option label="P1" value="P1" />
                <el-option label="P2" value="P2" />
              </el-select>
            </el-form-item>
            <el-form-item label="用例描述" class="wide">
              <el-input v-model="caseForm.description" type="textarea" :rows="3" placeholder="请输入用例描述" />
            </el-form-item>
            <el-form-item label="Body" class="wide">
              <el-input v-model="caseForm.bodyText" type="textarea" :rows="8" placeholder="请输入 JSON Body" />
            </el-form-item>
            <div class="wide">
              <div class="kv-title">
                <h4>断言</h4>
                <el-button size="small" @click="addCaseAssertionRow">添加</el-button>
              </div>
              <el-table :data="caseForm.assertionRows">
                <el-table-column label="断言类型" width="190">
                  <template #default="{ row }">
                    <el-select v-model="row.type">
                      <el-option v-for="option in assertionTypes" :key="option.value" :label="option.label" :value="option.value" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="JSONPath/路径">
                  <template #default="{ row }"><el-input v-model="row.path" placeholder="$.data.id / status_code" /></template>
                </el-table-column>
                <el-table-column label="操作符" width="120">
                  <template #default="{ row }"><el-input v-model="row.operator" placeholder="==" /></template>
                </el-table-column>
                <el-table-column label="期望值">
                  <template #default="{ row }"><el-input v-model="row.expected" placeholder="200 / success" /></template>
                </el-table-column>
                <el-table-column label="操作" width="90">
                  <template #default="{ $index }"><el-button size="small" type="danger" @click="removeCaseAssertionRow($index)">删除</el-button></template>
                </el-table-column>
              </el-table>
            </div>
          </el-form>
        </section>

        <el-dialog v-model="caseBodyDialogVisible" title="请求 Body" width="640px">
          <el-input v-model="caseBodyPreview" type="textarea" :rows="16" readonly />
          <template #footer>
            <el-button type="primary" @click="caseBodyDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

        <section v-if="active === 'execute'">
          <div class="toolbar">
            <h2>测试计划</h2>
            <el-button type="primary" @click="openCreatePlanPage">添加测试计划</el-button>
          </div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="计划名称">
              <el-input v-model="planSearch.name" placeholder="请输入计划名称" clearable @keyup.enter="searchPlans" />
            </el-form-item>
            <el-form-item label="项目">
              <el-select v-model="planSearch.project_id" placeholder="请选择项目" clearable @change="changePlanSearchProject">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="包含接口">
              <el-select v-model="planSearch.api_id" placeholder="请先选择项目" clearable :disabled="!planSearch.project_id">
                <el-option v-for="a in planSearchApis" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchPlans">搜索</el-button>
              <el-button @click="resetPlanSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="planList" row-key="id">
            <el-table-column type="expand">
              <template #default="{ row }">
                <el-table :data="row.cases || []" size="small" class="nested-table">
                  <el-table-column prop="name" label="用例名称" />
                  <el-table-column prop="api_name" label="接口" />
                  <el-table-column prop="priority" label="优先级" width="100" />
                  <el-table-column label="操作" width="100">
                    <template #default="{ row: caseRow }">
                      <el-button size="small" @click="openCaseDetailDialog(caseRow, row.environment_id, row.last_execution_id)">查看</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="计划名称" min-width="150" />
            <el-table-column prop="project_name" label="项目" />
            <el-table-column prop="environment_name" label="环境" />
            <el-table-column prop="api_name" label="包含接口" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="executionStatusType(row.last_status)">{{ row.last_status || '未执行' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="executor_name" label="执行用户" width="120" />
            <el-table-column prop="creator_name" label="创建用户" width="120" />
            <el-table-column label="执行时间" width="150">
              <template #default="{ row }">{{ formatMinute(row.last_executed_at) }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="150">
              <template #default="{ row }">{{ formatMinute(row.create_date) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="340" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button size="small" type="primary" @click="executePlan(row)">执行</el-button>
                  <el-button size="small" @click="openEditPlanPage(row)">编辑</el-button>
                  <el-button size="small" @click="openExecutionDetail(row)">查看进度</el-button>
                  <el-button size="small" type="danger" @click="deletePlan(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="planPagination.page"
              :page-size="planPagination.pageSize"
              :total="planPagination.total"
              @current-change="changePlanPage"
            />
          </div>
        </section>

        <section v-if="activePlanEditor" class="plan-editor-page">
          <div class="toolbar">
            <h2>{{ activePlanEditor.label }}</h2>
            <div class="toolbar-actions">
              <el-button @click="closePlanEditorFromPage(activePlanEditor)">关闭</el-button>
              <el-button type="primary" @click="savePlanEditor(activePlanEditor, true)">保存</el-button>
            </div>
          </div>

          <div class="editor-section">
            <h3>基础信息</h3>
            <el-form label-position="top" class="form-grid">
              <el-form-item label="项目">
                <el-select v-model="activePlanEditor.project_id" placeholder="请选择项目" @change="changePlanEditorProject(activePlanEditor)">
                  <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="环境">
                <el-select v-model="activePlanEditor.environment_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="markPlanEditorDirty(activePlanEditor)">
                  <el-option v-for="e in planEditorEnvironments(activePlanEditor)" :key="e.id" :label="e.name" :value="e.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="接口">
                <el-select v-model="activePlanEditor.api_id" placeholder="请先选择项目" :disabled="!activePlanEditor.project_id" @change="changePlanEditorApi(activePlanEditor)">
                  <el-option v-for="a in planEditorApis(activePlanEditor)" :key="a.id" :label="a.name" :value="a.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="测试计划名称">
                <el-input v-model="activePlanEditor.name" placeholder="请输入测试计划名称" @input="markPlanEditorDirty(activePlanEditor)" />
              </el-form-item>
            </el-form>
          </div>

          <div class="editor-section">
            <div class="toolbar compact-toolbar">
              <h3>测试用例</h3>
              <div class="toolbar-actions">
                <el-button type="primary" @click="loadPlanCandidateCases(activePlanEditor)">搜索</el-button>
                <el-button @click="addSelectedPlanCases(activePlanEditor)">添加</el-button>
              </div>
            </div>
            <el-table
              :data="activePlanEditor.candidateCases"
              size="small"
              row-key="id"
              @selection-change="changePlanCandidateSelection(activePlanEditor, $event)"
            >
              <el-table-column type="selection" width="48" />
              <el-table-column prop="name" label="用例名称" />
              <el-table-column prop="api_name" label="接口" />
              <el-table-column prop="priority" label="优先级" width="100" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" @click="openCaseDetailDialog(row, activePlanEditor.environment_id)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="editor-section">
            <h3>测试计划</h3>
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
                <el-tag size="small">{{ item.priority }}</el-tag>
                <el-button size="small" @click="openCaseDetailDialog(item, activePlanEditor.environment_id)">查看</el-button>
                <el-button size="small" type="danger" @click="removePlanQueueCase(activePlanEditor, index)">移除</el-button>
              </div>
              <el-empty v-if="activePlanEditor.queue.length === 0" description="暂无用例" />
            </div>
          </div>
        </section>

        <el-dialog v-model="caseDetailDialogVisible" title="用例详情" width="760px">
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
            <template v-if="caseDetail.response_snapshot?.decrypted_text !== undefined">
              <strong>响应密文</strong><pre>{{ formatJson(caseDetail.response_snapshot.encrypted_json) }}</pre>
              <strong>响应解密内容</strong><pre>{{ caseDetail.response_snapshot.decrypted_text }}</pre>
            </template>
            <template v-else>
              <strong>返回报文</strong><pre>{{ formatJson(caseDetail.response_snapshot) }}</pre>
            </template>
          </div>
          <template #footer>
            <el-button type="primary" @click="caseDetailDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

        <el-dialog v-model="executionDetailDialogVisible" title="执行进度" width="820px">
          <el-descriptions v-if="executionDetail.task" :column="3" border>
            <el-descriptions-item label="状态">{{ executionDetail.task.status }}</el-descriptions-item>
            <el-descriptions-item label="汇总">{{ formatJson(executionDetail.task.summary) }}</el-descriptions-item>
          </el-descriptions>
          <el-table :data="executionDetail.results" size="small" class="sub">
            <el-table-column prop="case_name" label="用例名称" min-width="140" />
            <el-table-column prop="api_name" label="接口" min-width="140" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
            <el-table-column prop="error_message" label="错误信息" />
          </el-table>
          <template #footer>
            <el-button type="primary" @click="executionDetailDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

        <section v-if="active === 'reports'">
          <div class="toolbar"><h2>报告中心</h2></div>
          <el-form class="search-form" label-position="top">
            <el-form-item label="测试计划名称">
              <el-input v-model="reportSearch.name" placeholder="请输入测试计划名称" clearable @keyup.enter="searchReports" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="reportSearch.status" placeholder="请选择状态" clearable>
                <el-option label="queued" value="queued" />
                <el-option label="running" value="running" />
                <el-option label="passed" value="passed" />
                <el-option label="failed" value="failed" />
                <el-option label="error" value="error" />
              </el-select>
            </el-form-item>
            <div class="search-actions">
              <el-button type="primary" @click="searchReports">搜索</el-button>
              <el-button @click="resetReportSearch">重置</el-button>
            </div>
          </el-form>
          <el-table :data="reportList">
            <el-table-column prop="target_name" label="测试计划名称" min-width="160" />
            <el-table-column prop="project_name" label="项目" />
            <el-table-column prop="environment_name" label="环境" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="执行时间" width="150">
              <template #default="{ row }">{{ formatMinute(row.ended_at || row.started_at || row.create_date) }}</template>
            </el-table-column>
            <el-table-column prop="executor_name" label="执行用户" width="120" />
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-link :href="`/api/executions/${row.id}/report`" target="_blank">查看报告</el-link>
                  <el-button size="small" type="danger" @click="deleteReport(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :current-page="reportPagination.page"
              :page-size="reportPagination.pageSize"
              :total="reportPagination.total"
              @current-change="changeReportPage"
            />
          </div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type User } from './api'

type AppTab = { name: string; label: string; closable: boolean }
type KeyValueRow = { id: number; key: string; value: string }
type CaseAssertionRow = { id: number; type: string; path: string; operator: string; expected: string }
type ApiEncryption = {
  enabled: boolean
  mode: 'none' | 'rsa_aes_sm3'
  encryptRequest: boolean
  decryptResponse: boolean
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
  activePanel: '' | 'query' | 'headers' | 'body' | 'pre-script' | 'encryption'
  queryRows: KeyValueRow[]
  headerRows: KeyValueRow[]
  preScript: string
  encryption: ApiEncryption
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
const caseForm = reactive({ id: undefined as number | undefined, project_id: undefined as number | undefined, api_id: undefined as number | undefined, name: '', description: '', priority: 'P2', bodyText: '{}', assertionRows: [] as CaseAssertionRow[] })
const execForm = reactive({ project_id: undefined as number | undefined, environment_id: undefined as number | undefined, target_id: undefined as number | undefined })
const apiEditors = reactive<Record<string, ApiEditor>>({})
const planEditors = reactive<Record<string, PlanEditor>>({})
const avatarText = computed(() => me.value?.username.slice(0, 1).toUpperCase() || 'U')
const activeApiEditor = computed(() => apiEditors[active.value])
const activePlanEditor = computed(() => planEditors[active.value])
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
    dirty: false
  }
  return editor
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

function apiPayload(editor: ApiEditor) {
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
    }
  }
}

function validateApiEditor(editor: ApiEditor) {
  const payload = apiPayload(editor)
  if (!payload.project_id) {
    ElMessage.warning('请选择项目')
    return null
  }
  if (!payload.name) {
    ElMessage.warning('请输入接口名称')
    return null
  }
  if (!payload.path) {
    ElMessage.warning('请输入接口路径')
    return null
  }
  if (apiNameExists(payload.project_id, payload.name, editor.apiId)) {
    ElMessage.warning('接口名称已存在')
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
      ElMessage.success('接口已更新')
    } else {
      const { data } = await api.post('/apis', payload)
      ElMessage.success('接口已创建')
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
    ElMessage.error(error?.response?.data?.detail || '接口保存失败')
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
    await ElMessageBox.confirm('当前接口内容尚未保存，是否保存后关闭？', '关闭接口', {
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
    await ElMessageBox.confirm('确认删除该接口吗？', '删除接口', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/apis/${row.id}`)
    ElMessage.success('接口已删除')
    await refreshApisAfterDelete()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '接口删除失败')
  }
}

function resetCaseForm() {
  caseForm.id = undefined
  caseForm.project_id = undefined
  caseForm.api_id = undefined
  caseForm.name = ''
  caseForm.description = ''
  caseForm.priority = 'P2'
  caseForm.bodyText = '{}'
  caseForm.assertionRows = []
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
  caseForm.priority = row.priority || 'P2'
  caseForm.bodyText = JSON.stringify(row.request_body ?? {}, null, 2)
  caseForm.assertionRows = caseAssertionsToRows(row.assertions)
  openRuntimeTab({ name: `case-edit-${row.id}`, label: `编辑用例-${row.id}`, closable: true })
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

function validateCaseForm() {
  if (!caseForm.project_id) {
    ElMessage.warning('请选择项目')
    return null
  }
  if (!caseForm.api_id) {
    ElMessage.warning('请选择接口')
    return null
  }
  const name = caseForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入用例名称')
    return null
  }
  const requestBody = parseJson(caseForm.bodyText, undefined)
  if (requestBody === undefined) {
    ElMessage.warning('Body 必须是合法 JSON')
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
    extractors: [],
    tags: caseForm.description.trim(),
    priority: caseForm.priority,
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
      ElMessage.success('用例已更新')
    } else {
      await api.post('/cases', payload)
      ElMessage.success('用例已创建')
    }
    caseSearch.project_id = payload.project_id
    caseSearch.api_id = payload.api_id
    resetCaseForm()
    await loadCases()
    await refreshAllCases()
    closeCaseEditorPage()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '用例保存失败')
  }
}

async function deleteCase(row: any) {
  try {
    await ElMessageBox.confirm('确认删除该用例吗？', '删除用例', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  try {
    await api.delete(`/cases/${row.id}`)
    ElMessage.success('用例已删除')
    await loadCases()
    if (caseList.value.length === 0 && casePagination.page > 1) {
      casePagination.page -= 1
      await loadCases()
    }
    await refreshAllCases()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '用例删除失败')
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
    ElMessage.warning('请选择项目')
    return null
  }
  if (!editor.environment_id) {
    ElMessage.warning('请选择环境')
    return null
  }
  if (!editor.api_id) {
    ElMessage.warning('请选择接口')
    return null
  }
  const name = editor.name.trim()
  if (!name) {
    ElMessage.warning('请输入测试计划名称')
    return null
  }
  if (planNameExists(editor.project_id, name, editor.planId)) {
    ElMessage.warning('测试计划名称已存在')
    return null
  }
  if (editor.queue.length === 0) {
    ElMessage.warning('请至少添加一条测试用例')
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
    ElMessage.warning('请先选择项目、环境和接口')
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
      ElMessage.success('测试计划已更新')
    } else {
      const { data } = await api.post('/plans', payload)
      ElMessage.success('测试计划已创建')
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
    ElMessage.error(error?.response?.data?.detail || '测试计划保存失败')
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
    await ElMessageBox.confirm('当前测试计划内容尚未保存，是否保存后关闭？', '关闭测试计划', {
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
    await ElMessageBox.confirm('确认删除该测试计划吗？', '删除测试计划', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/plans/${row.id}`)
  ElMessage.success('测试计划已删除')
  await loadPlans()
}

async function executePlan(row: any) {
  await api.post(`/plans/${row.id}/execute`)
  ElMessage.success('执行任务已提交')
  await Promise.all([loadPlans(), loadReports(), api.get('/executions').then(r => executions.value = r.data)])
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

function executionStatusType(status: string) {
  if (status === 'passed') return 'success'
  if (status === 'failed' || status === 'error') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

async function openExecutionDetail(row: any) {
  if (!row.last_execution_id) {
    ElMessage.warning('该测试计划暂无执行记录')
    return
  }
  const { data } = await api.get(`/executions/${row.last_execution_id}`)
  executionDetail.task = data.task
  executionDetail.results = data.results || []
  executionDetailDialogVisible.value = true
}

async function deleteReport(row: any) {
  try {
    await ElMessageBox.confirm('确认删除该报告吗？删除后报告中心将不再展示。', '删除报告', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await api.delete(`/executions/${row.id}`)
  ElMessage.success('报告已删除')
  await loadReports()
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
