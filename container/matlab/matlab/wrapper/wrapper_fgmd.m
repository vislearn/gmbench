function wrapper_fgmd(file)

var1 = {'K','Ct','gph1','gph2','KP','KQ','offset'};
data = load(file,var1{:});

K_orig = data.K; % original cost matrix
offset = data.offset;

Ct = data.Ct;
gph1 = data.gph1;
gph2 = data.gph2;
KP = - data.KP;
KQ = - data.KQ;
gphs = {gph1,gph2};

[n1,n2] = size(Ct);

tstart = tic;
fprintf('Start optimization: \n')
fprintf('Model: n1: %g n2: %g \n', n1, n2)

par.dummy = 0;
asg = fgmD(KP, full(KQ), Ct, gphs, [], par)

X = asg.X

curr_score = X(:)' * K_orig * X(:);

fprintf('time: %f ',toc(tstart))
fprintf('upper_bound: %f ', full(curr_score)+cast(offset,'like',full(curr_score)))
indices = 1:n2;
matching = reshape(X,size(Ct))*indices';
fprintf('labeling: [')
fprintf('%g,',matching(1:end-1))
fprintf('%g] \n',matching(end))
